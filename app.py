from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
import functools
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import time
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from textblob import TextBlob
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "super_secret_key_for_demo_only"  # In production, use environment variable

# SAFE LIMITS
SAFE_LIMIT_MG_L = 0.5
RECOMMENDED_MG_KG = 0.02

# Dictionary for specific limits (used in detection testing)
SAFE_LIMITS = {
    "milk": 0.05,
    "meat": 0.10,
    "water": 0.01,
    "default": 0.05
}

# Store data
FEEDBACK_FILE = "feedback_data.json"
ANALYSIS_HISTORY_FILE = "analysis_history.json"
USERS_FILE = "users.json"

# EMAIL CONFIGURATION (Placeholders)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "guruar0821@gmail.com"
SENDER_PASSWORD = "wvwt cfyj hoad somk"

def send_email(to_email, name, rating, message, attachment_path=None):
    try:
        if "your_email" in SENDER_EMAIL:
            print("❌ Email not sent: Credentials not configured.")
            return False

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = "Your Steroid Analysis Report & Feedback Confirmation"

        # Email body
        body = f"Dear {name},\n\nThank you for your feedback!\n\nDetails:\n- Rating: {rating}/5\n- Message: {message}\n\n"
        if attachment_path:
            body += "Please find your official analysis report attached to this email.\n\n"
        body += "Warm regards,\nThe Safety Assurance Team"
        
        msg.attach(MIMEText(body, 'plain'))

        # Attachment logic
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(attachment_path)}",
                )
                msg.attach(part)
                print(f"📎 Attachment added: {attachment_path}")
            except Exception as e:
                print(f"⚠️ Failed to attach file: {str(e)}")

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD.replace(" ", ""))  # Handle spaces in app password
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def login_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r") as f:
            return json.load(f)
    return []

def save_feedback(feedback_list):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback_list, f, indent=2)

def load_analysis_history():
    if os.path.exists(ANALYSIS_HISTORY_FILE):
        with open(ANALYSIS_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_analysis_history(history_list):
    with open(ANALYSIS_HISTORY_FILE, "w") as f:
        json.dump(history_list, f, indent=2)

def get_statistics():
    feedback_list = load_feedback()
    history = load_analysis_history()
    
    total_analyses = len(history)
    avg_rating = sum([int(f.get("rating", 5)) for f in feedback_list]) / len(feedback_list) if feedback_list else 0
    safe_samples = len([h for h in history if h.get("level") == "safe"])
    danger_samples = len([h for h in history if h.get("level") == "danger"])
    
    return {
        "total_analyses": total_analyses,
        "safe_samples": safe_samples,
        "danger_samples": danger_samples,
        "avg_rating": round(avg_rating, 1),
        "total_users": len(feedback_list)
    }

@app.route("/")
# @login_required  <-- Removed to make this public
def home():
    stats = get_statistics()
    return render_template("safety_dashboard.html", stats=stats)

# --- FEATURE 2: DYNAMIC GRAPH GENERATION ---
def generate_graph(detected, safe_limit):
    """Generates a bar chart comparing detected level vs safe limit."""
    plt.figure(figsize=(6, 4))
    
    # Data
    categories = ['Safe Limit', 'Detected Level']
    values = [safe_limit, detected]
    colors = ['#2e7d32', '#c62828' if detected > safe_limit else '#2e7d32']
    
    # Plot
    bars = plt.bar(categories, values, color=colors, width=0.5)
    
    # Styling
    plt.title('Steroid Level Analysis', fontsize=14, fontweight='bold', color='#333')
    plt.ylabel('Concentration (mg/L)', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.2f}',
                 ha='center', va='bottom', fontweight='bold')
    
    # Save
    timestamp = int(time.time())
    filename = f"plot_{timestamp}.png"
    filepath = os.path.join("static", "plots", filename)
    
    # Ensure directory exists
    os.makedirs(os.path.join("static", "plots"), exist_ok=True)
    
    plt.savefig(filepath, bbox_inches='tight', transparent=True)
    plt.close()
    return filename
# ---------------------------------------------

@app.route("/detection-testing", methods=["GET", "POST"])
@login_required
def detection_testing():
    plot_url = None # Initialize at the absolute top
    result = None
    warning = None
    last_test = None

    if request.method == "POST":
        try:
            sample_type = request.form.get("sample_type", "milk")
            sensor_val = float(request.form["sensor"])
            weight = float(request.form["weight"])

            # Main Logic (Detection)
            detected_level = round(sensor_val / weight, 2)
            safe_limit = SAFE_LIMITS.get(sample_type, 0.05)

            status_level = "safe"
            if detected_level > safe_limit:
                status_level = "danger"
                warning = f"⚠️ DANGER: Exceeds safe limit of {safe_limit} mg/kg!"
            elif detected_level > (safe_limit * 0.8):
                status_level = "caution"
                warning = f"⚠️ CAUTION: Approaching limit of {safe_limit} mg/kg."
            else:
                warning = "✅ SAFE: Level is within acceptable limits."

            result = {
                "detected": detected_level,
                "safe_dose": safe_limit,
                "level": status_level
            }
            
            # Use Feature 2: Generate Dynamic Graph
            plot_filename = generate_graph(detected_level, safe_limit)
            plot_url = url_for('static', filename=f'plots/{plot_filename}')
            
            # Save History
            history = load_analysis_history()
            analysis_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sample_type": sample_type,
                "detected_level": detected_level,
                "level": status_level,
                "plot_url": plot_url
            }
            history.append(analysis_entry)
            save_analysis_history(history)
            
            # AUTOMATE PDF GENERATION (so it's ready for email)
            try:
                # We reuse the logic from download_report but don't return the file
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(200, 10, "Steroid Detection & Safety System", ln=True, align='C')
                pdf.set_font("Arial", "I", 12)
                pdf.cell(200, 10, "Official Analysis Report", ln=True, align='C')
                pdf.line(10, 30, 200, 30)
                pdf.ln(20)
                pdf.set_font("Arial", "", 12)
                pdf.cell(200, 10, f"User: {session.get('user', 'Guest')}", ln=True)
                pdf.cell(200, 10, f"Date: {analysis_entry['timestamp']}", ln=True)
                pdf.ln(10)
                pdf.set_font("Arial", "B", 14)
                pdf.cell(200, 10, "Analysis Results:", ln=True)
                pdf.set_font("Arial", "", 12)
                pdf.cell(100, 10, f"Sample Type: {sample_type.title()}", ln=True)
                pdf.cell(100, 10, f"Detected Level: {detected_level} mg/L", ln=True)
                
                pdf.set_font("Arial", "B", 12)
                if status_level == 'safe': pdf.set_text_color(46, 125, 50)
                elif status_level == 'danger': pdf.set_text_color(198, 40, 40)
                else: pdf.set_text_color(249, 168, 37)
                pdf.cell(100, 10, f"Safety Status: {status_level.upper()}", ln=True)
                
                pdf.set_text_color(0, 0, 0)
                pdf.ln(20)
                pdf.set_font("Courier", "", 10)
                pdf.cell(200, 10, "[ Automatically generated report ]", ln=True, align='C')
                
                report_dir = os.path.join("static", "reports")
                os.makedirs(report_dir, exist_ok=True)
                report_path = os.path.join(report_dir, f"report_{int(time.time())}.pdf")
                pdf.output(report_path)
                print(f"📄 Auto-generated report: {report_path}")
            except Exception as e:
                print(f"⚠️ Failed to auto-generate PDF: {str(e)}")

            # Update last_test for immediate display after post
            last_test = analysis_entry

        except ValueError:
            warning = "❌ Invalid input. Please enter valid numbers."
        except Exception as e:
            warning = f"❌ Error during analysis: {str(e)}"

    # Get last test result if not just submitted
    if request.method == "GET":
        history = load_analysis_history()
        last_test = history[-1] if history else None
        # If there's a last test, set its plot_url for display
        if last_test and "plot_url" in last_test:
            plot_url = last_test["plot_url"]
        
    return render_template("detection_testing.html", result=result, warning=warning, last_test=last_test, plot_url=plot_url)



@app.route("/community-reviews", methods=["GET", "POST"])
@login_required
def community_reviews():
    if request.method == "POST":
        try:
            user_feedback = {
                "name": request.form.get("name", "Anonymous"),
                "email": request.form.get("email", ""),
                "message": request.form.get("message", ""),
                "rating": request.form.get("rating", "5"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # --- AI SENTIMENT ANALYSIS ---
            if user_feedback["message"]:
                blob = TextBlob(user_feedback["message"])
                polarity = blob.sentiment.polarity
                if polarity > 0.1:
                    user_feedback["sentiment"] = "Positive"
                elif polarity < -0.1:
                    user_feedback["sentiment"] = "Negative"
                else:
                    user_feedback["sentiment"] = "Neutral"
            else:
                user_feedback["sentiment"] = "Neutral"
            # -----------------------------
            
            feedback_list = load_feedback()
            feedback_list.insert(0, user_feedback) # Add to top
            save_feedback(feedback_list)
            
            # Send Email Notification with Attachment
            if user_feedback.get("email"):
                # Retrieve latest report path from history if available
                history = load_analysis_history()
                attachment_path = None
                if history:
                    last_entry = history[-1]
                    # We need to construct the local path from the plot_url or similar
                    # However, Feature 3 saves reports to static/reports/report_XYZ.pdf
                    # Let's check for the most recent file in static/reports
                    report_dir = os.path.join("static", "reports")
                    if os.path.exists(report_dir):
                        reports = [os.path.join(report_dir, f) for f in os.listdir(report_dir) if f.endswith(".pdf")]
                        if reports:
                            # Use the most recently modified file
                            attachment_path = max(reports, key=os.path.getmtime)
                
                send_email(user_feedback["email"], user_feedback["name"], user_feedback["rating"], user_feedback["message"], attachment_path)

            success_message = "✅ Thank you for your feedback!"
            feedback_list = load_feedback()
            return render_template("community_reviews.html", success_message=success_message, feedback_list=feedback_list)
        except Exception as e:
            error_message = f"❌ Error saving feedback: {str(e)}"
            feedback_list = load_feedback()
            return render_template("community_reviews.html", error_message=error_message, feedback_list=feedback_list)
    
    feedback_list = load_feedback()
    return render_template("community_reviews.html", feedback_list=feedback_list)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        
        if username in users and users[username] == password:
            session["user"] = username
            return redirect(url_for("detection_testing"))
        else:
            return render_template("login.html", error="Invalid username or password")
            
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    users = load_users()
    
    if username in users:
        return render_template("login.html", error="Username already exists")
    
    users[username] = password
    save_users(users)
    session["user"] = username
    return redirect(url_for("detection_testing"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))



# --- FEATURE 3: PDF REPORT GENERATION ---
@app.route("/download_report")
@login_required
def download_report():
    history = load_analysis_history()
    if not history:
        return "No analysis data found.", 404
        
    last_test = history[-1]
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Header
    pdf.cell(200, 10, "Steroid Detection & Safety System", ln=True, align='C')
    pdf.set_font("Arial", "I", 12)
    pdf.cell(200, 10, "Official Analysis Report", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(20)
    
    # User Info
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"User: {session.get('user', 'Guest')}", ln=True)
    pdf.cell(200, 10, f"Date: {last_test.get('timestamp')}", ln=True)
    pdf.ln(10)
    
    # Result Details
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Analysis Results:", ln=True)
    pdf.set_font("Arial", "", 12)
    
    pdf.cell(100, 10, f"Sample Type: {last_test.get('sample_type', 'N/A').title()}", ln=True)
    pdf.cell(100, 10, f"Detected Level: {last_test.get('detected_level')} mg/L", ln=True)
    
    # Status Logic for Color/Text
    status = last_test.get('level', 'unknown').upper()
    pdf.set_font("Arial", "B", 12)
    if status == 'SAFE':
        pdf.set_text_color(46, 125, 50) # Green
    elif status == 'DANGER':
        pdf.set_text_color(198, 40, 40) # Red
    else:
        pdf.set_text_color(249, 168, 37) # Yellow/Orange
        
    pdf.cell(100, 10, f"Safety Status: {status}", ln=True)
    
    # Reset color
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    
    # Verification
    pdf.set_font("Courier", "", 10)
    pdf.cell(200, 10, "[ This report is automatically generated by the AI Safety System ]", ln=True, align='C')
    
    # Save (temp) and Send
    filename = f"report_{int(time.time())}.pdf"
    filepath = os.path.join("static", "reports", filename)
    os.makedirs(os.path.join("static", "reports"), exist_ok=True)
    pdf.output(filepath)
    
    return send_file(filepath, as_attachment=True)
# ---------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
import functools
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import math
import time
import json
import random
import threading
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from textblob import TextBlob
from fpdf import FPDF

# Try to import pyserial (optional — graceful fallback if not installed)
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("⚠️  pyserial not installed. Run: pip install pyserial")

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
SENDER_EMAIL = "lactologic52@gmail.com"
SENDER_PASSWORD = "hqqm kwrf hlyq yqmu"

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
# --- FEATURE 2: DYNAMIC GRAPH GENERATION ---
def generate_graph(history_data, current_detected, current_timestamp, safe_limit, sample_type):
    """Generates a trend line chart comparing detected levels vs safe limit over time."""
    # Light theme background
    plt.figure(figsize=(10, 5), facecolor='#f8f9fa')
    
    # Prepare Data
    detected_values = [h.get('detected_level', 0) for h in history_data]
    timestamps = [h.get('timestamp', '')[11:16] for h in history_data] # Extract HH:MM
    
    # Add current test to plot data
    detected_values.append(current_detected)
    timestamps.append(current_timestamp[11:16]) # Extract HH:MM
    
    # X-axis points (Time Points)
    x = range(len(detected_values)) # 0 to N-1
    
    # Plot Safe Limit Line
    # Dark Green for Safe Limit as requested
    plt.plot(x, [safe_limit] * len(x), label='Safe Limit', color='#2e7d32', linewidth=2.5, marker='o', zorder=5)
    
    # Determine Status Color of Current Test (for Line Color)
    if current_detected <= safe_limit:
        line_color = '#66bb6a' # Light Green for Safe
        status_text = "SAFE"
    else:
        line_color = '#ef5350' # Red for Danger
        status_text = "DANGER"
    
    # Plot Trend Line (Color based on CURRENT status to show trend direction)
    plt.plot(x, detected_values, label=f'Detected Level ({status_text})', 
             color=line_color, linewidth=2.5, zorder=6)

    # Plot Individual Points (Color based on THEIR status to show history correctly)
    point_colors = []
    for val in detected_values:
        if val <= safe_limit:
            point_colors.append('#66bb6a') # Light Green
        else:
            point_colors.append('#ef5350') # Red

    plt.scatter(x, detected_values, color=point_colors, s=100, marker='s', zorder=7, edgecolors='white')

    # Styling
    # Light Theme Graph Styling
    plt.title('Steroid Level Analysis - Real-Time Trend', fontsize=12, fontweight='bold', color='#333333')
    plt.ylabel('mg/L', fontsize=10, color='#333333')
    plt.xlabel('Time (HH:MM)', fontsize=10, color='#333333')
    
    # Ticks styling
    plt.xticks(x, timestamps, color='#333333', rotation=45) 
    plt.yticks(color='#333333')
    
    # Grid styling
    plt.grid(True, linestyle='--', alpha=0.5, color='#e0e0e0')
    
    # Legend styling
    legend = plt.legend(loc='upper right', facecolor='white', edgecolor='#cccccc')
    plt.setp(legend.get_texts(), color='#333333') # Legend text color

    # Add borders/limits
    max_y = max(max(detected_values), safe_limit)
    if max_y == 0: max_y = 1
    plt.ylim(0, max_y * 1.4)

    # Set axes colors
    ax = plt.gca()
    ax.set_facecolor('#f8f9fa') # Light gray plot area
    for spine in ax.spines.values():
        spine.set_color('#333333') # Dark gray spines

    # Save
    timestamp_file = int(time.time())
    filename = f"plot_{timestamp_file}.png"
    filepath = os.path.join("static", "plots", filename)
    
    # Ensure directory exists
    os.makedirs(os.path.join("static", "plots"), exist_ok=True)
    
    # Save with transparent background (or keep light background if preferred)
    # Keeping facecolor from figure for consistency
    plt.savefig(filepath, bbox_inches='tight', facecolor='#f8f9fa')
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

            # Auto-calculate pH from sensor reading
            # Formula: simulates a real pH electrode (higher sensor voltage → more acidic)
            # Typical milk pH: 6.4–6.8 | water: ~7.0 | contaminated samples drift acidic
            raw_ph = 7.0 - (sensor_val - 1.5) / 0.18
            ph_value = round(max(0.0, min(14.0, raw_ph)), 2)

            # pH Status
            if ph_value < 6.5:
                ph_status = "acidic"
            elif ph_value > 7.5:
                ph_status = "alkaline"
            else:
                ph_status = "neutral"

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
                "level": status_level,
                "ph_value": round(ph_value, 2),
                "ph_status": ph_status
            }
            
            # Prepare History Data for Trend Graph (Filter by Sample Type & User)
            history = load_analysis_history()
            current_user = session.get("user")
            
            # STRICT Filter history: Same sample type AND Same user (NO LEGACY/SHARED DATA)
            relevant_history = [
                h for h in history 
                if h.get("sample_type", "milk") == sample_type and 
                h.get("user") == current_user
            ]
            
            # Take last 9 records to make graph readable (total 10 points with current)
            recent_history = relevant_history[-9:]

            # Generate Timestamp for current test
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Use Feature 2: Generate Dynamic Graph
            plot_filename = generate_graph(recent_history, detected_level, current_timestamp, safe_limit, sample_type)
            plot_url = url_for('static', filename=f'plots/{plot_filename}')
            
            # Save History
            history = load_analysis_history()
            analysis_entry = {
                "timestamp": current_timestamp,
                "sample_type": sample_type,
                "detected_level": detected_level,
                "level": status_level,
                "ph_value": round(ph_value, 2),
                "ph_status": ph_status,
                "plot_url": plot_url,
                "user": current_user  # Save user with record
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
                pdf.cell(100, 10, f"pH Value: {round(ph_value, 2)} ({ph_status.title()})", ln=True)
                
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
        current_user = session.get("user")
        
        # STRICT Filter history: Same logic as POST (NO LEGACY/SHARED DATA)
        relevant_history = [
            h for h in history 
            if h.get("user") == current_user
        ]
        
        last_test = relevant_history[-1] if relevant_history else None
        # If there's a last test, set its plot_url for display
        if last_test and "plot_url" in last_test:
            plot_url = last_test["plot_url"]
        
    return render_template("detection_testing.html", result=result, warning=warning, last_test=last_test, plot_url=plot_url)

@app.route("/simulation")
def simulation():
    return render_template("simulation.html")



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


# =============================================
# HARDWARE SERIAL STATE
# =============================================
hw_lock = threading.Lock()
hw = {
    "connected": False,
    "port": None,
    "baud": 9600,
    "error": None,
    "serial_obj": None,
    "thread": None,
    "data": None,        # Latest parsed reading from Arduino
    "last_update": None  # Timestamp of last successful read
}


def serial_reader_thread():
    """Background thread: continuously reads JSON lines from Arduino over serial."""
    with hw_lock:
        port = hw["port"]
        baud = hw["baud"]

    print(f"🔌 Serial thread starting on {port} @ {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=2)
        with hw_lock:
            hw["serial_obj"] = ser
            hw["error"] = None
        print(f"✅ Arduino connected on {port}")

        while True:
            with hw_lock:
                if not hw["connected"]:
                    break
            try:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                # Only process lines that look like JSON
                if line.startswith("{"):
                    parsed = json.loads(line)
                    parsed["timestamp"] = datetime.now().strftime("%H:%M:%S")
                    with hw_lock:
                        hw["data"] = parsed
                        hw["last_update"] = time.time()
            except json.JSONDecodeError:
                pass   # Skip malformed lines
            except Exception as e:
                with hw_lock:
                    hw["error"] = str(e)
                    hw["connected"] = False
                print(f"❌ Serial read error: {e}")
                break

        ser.close()
        print(f"🔌 Serial port {port} closed.")
    except Exception as e:
        with hw_lock:
            hw["connected"] = False
            hw["error"] = f"Cannot open {port}: {str(e)}"
        print(f"❌ Cannot open serial port {port}: {e}")


# =============================================
# REAL-TIME DATA API ENDPOINTS
# =============================================

@app.route("/api/realtime-data")
def api_realtime_data():
    """Returns live system statistics and recent analysis history for real-time dashboard."""
    history = load_analysis_history()
    feedback_list = load_feedback()

    total_analyses = len(history)
    safe_count = len([h for h in history if h.get("level") == "safe"])
    danger_count = len([h for h in history if h.get("level") == "danger"])
    caution_count = len([h for h in history if h.get("level") == "caution"])
    avg_rating = round(sum([int(f.get("rating", 5)) for f in feedback_list]) / len(feedback_list), 1) if feedback_list else 0

    recent = history[-5:][::-1]
    safe_pct = round((safe_count / total_analyses * 100), 1) if total_analyses > 0 else 0

    with hw_lock:
        hw_connected = hw["connected"]
        hw_port = hw["port"]

    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_time": datetime.now().strftime("%H:%M:%S"),
        "total_analyses": total_analyses,
        "safe_count": safe_count,
        "danger_count": danger_count,
        "caution_count": caution_count,
        "safe_percentage": safe_pct,
        "avg_rating": avg_rating,
        "total_reviews": len(feedback_list),
        "hardware_connected": hw_connected,
        "hardware_port": hw_port,
        "recent_analyses": [
            {
                "timestamp": h.get("timestamp", ""),
                "sample_type": h.get("sample_type", "unknown"),
                "detected_level": h.get("detected_level", 0),
                "level": h.get("level", "unknown"),
                "ph_value": h.get("ph_value", None),
                "ph_status": h.get("ph_status", None),
                "user": h.get("user", "Anonymous")
            } for h in recent
        ]
    })


@app.route("/api/sensor-stream")
def api_sensor_stream():
    """Returns real Arduino sensor data if hardware connected, else simulated fallback."""
    t = time.time()
    safe_limit = SAFE_LIMITS.get("milk", 0.05)

    # ── Try HARDWARE data first ──────────────────────────────
    with hw_lock:
        hw_connected = hw["connected"]
        hw_data = hw["data"]
        hw_last = hw["last_update"]

    if hw_connected and hw_data and hw_last and (t - hw_last) < 5.0:
        ph_value      = round(float(hw_data.get("ph", 7.0)), 2)
        sensor_reading = round(float(hw_data.get("sensor", 1.0)), 2)
        temperature   = round(float(hw_data.get("temp", 25.0)), 1)
        detected_level = round(sensor_reading, 2)

        if detected_level > safe_limit:
            status = "danger"
        elif detected_level > safe_limit * 0.8:
            status = "caution"
        else:
            status = "safe"

        if ph_value < 6.5:
            ph_status = "acidic"
        elif ph_value > 7.5:
            ph_status = "alkaline"
        else:
            ph_status = "neutral"

        return jsonify({
            "source":         "hardware",
            "timestamp":      hw_data.get("timestamp", datetime.now().strftime("%H:%M:%S")),
            "unix_time":      round(t, 2),
            "sensor_reading": sensor_reading,
            "detected_level": detected_level,
            "ph_value":       ph_value,
            "ph_status":      ph_status,
            "sample_type":    "milk",
            "safe_limit":     safe_limit,
            "status":         status,
            "temperature":    temperature,
            "signal_strength": 100.0,
        })

    # ── Fallback: SIMULATED data ─────────────────────────────
    base  = 2.0
    wave  = math.sin(t * 0.3) * 0.8
    noise = (random.random() - 0.5) * 0.3
    sensor_reading = round(max(0.1, base + wave + noise), 2)

    raw_ph   = 7.0 - (sensor_reading - 1.5) / 0.18
    ph_value = round(max(0.0, min(14.0, raw_ph)), 2)

    sample_types  = ["milk", "meat", "water"]
    sample_type   = sample_types[int(t / 10) % 3]
    safe_limit    = SAFE_LIMITS.get(sample_type, 0.05)
    detected_level = round(sensor_reading, 2)

    if detected_level > safe_limit:
        status = "danger"
    elif detected_level > safe_limit * 0.8:
        status = "caution"
    else:
        status = "safe"

    return jsonify({
        "source":         "simulation",
        "timestamp":      datetime.now().strftime("%H:%M:%S"),
        "unix_time":      round(t, 2),
        "sensor_reading": sensor_reading,
        "detected_level": detected_level,
        "ph_value":       ph_value,
        "ph_status":      "neutral",
        "sample_type":    sample_type,
        "safe_limit":     safe_limit,
        "status":         status,
        "signal_strength": round(random.uniform(85, 100), 1),
        "temperature":    round(22.0 + math.sin(t * 0.1) * 2 + random.uniform(-0.2, 0.2), 1),
    })


@app.route("/api/live-stats")
def api_live_stats():
    """Quick summary endpoint for the dashboard ticker strip."""
    stats = get_statistics()
    stats["server_time"] = datetime.now().strftime("%H:%M:%S")
    stats["date"] = datetime.now().strftime("%d %b %Y")
    return jsonify(stats)


# =============================================
# HARDWARE / SERIAL MANAGEMENT ENDPOINTS
# =============================================

@app.route("/api/serial-ports")
def api_serial_ports():
    """Returns list of available COM ports on the machine."""
    if not SERIAL_AVAILABLE:
        return jsonify({"error": "pyserial not installed. Run: pip install pyserial", "ports": []})
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "port":        p.device,
            "description": p.description,
            "hwid":        p.hwid
        })
    return jsonify({"ports": ports})


@app.route("/api/connect-serial", methods=["POST"])
def api_connect_serial():
    """Connect to Arduino on the specified COM port."""
    if not SERIAL_AVAILABLE:
        return jsonify({"success": False, "error": "pyserial not installed. Run: pip install pyserial"}), 500

    data = request.get_json()
    port = data.get("port", "").strip()
    baud = int(data.get("baud", 9600))

    if not port:
        return jsonify({"success": False, "error": "No COM port specified"}), 400

    # Stop any existing connection first
    with hw_lock:
        if hw["connected"]:
            hw["connected"] = False   # Signal thread to stop
        hw["port"]      = port
        hw["baud"]      = baud
        hw["connected"] = True
        hw["error"]     = None
        hw["data"]      = None
        hw["last_update"] = None

    # Start the reader thread
    t = threading.Thread(target=serial_reader_thread, daemon=True)
    with hw_lock:
        hw["thread"] = t
    t.start()

    return jsonify({"success": True, "message": f"Connecting to {port} @ {baud} baud...", "port": port})


@app.route("/api/disconnect-serial", methods=["POST"])
def api_disconnect_serial():
    """Disconnect from Arduino."""
    with hw_lock:
        hw["connected"] = False
        hw["data"]      = None
        hw["error"]     = None
        if hw["serial_obj"]:
            try:
                hw["serial_obj"].close()
            except Exception:
                pass
            hw["serial_obj"] = None
    return jsonify({"success": True, "message": "Disconnected from hardware"})


@app.route("/api/hardware-status")
def api_hardware_status():
    """Returns current hardware connection status and latest sensor reading."""
    with hw_lock:
        connected  = hw["connected"]
        port       = hw["port"]
        error      = hw["error"]
        data       = hw["data"]
        last_upd   = hw["last_update"]

    stale = False
    if connected and last_upd and (time.time() - last_upd) > 5:
        stale = True

    return jsonify({
        "connected":       connected,
        "port":            port,
        "error":           error,
        "stale":           stale,
        "serial_available": SERIAL_AVAILABLE,
        "latest_reading":  data,
        "last_update":     last_upd
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
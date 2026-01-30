from flask import Flask, render_template, request, jsonify
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime

app = Flask(__name__)

# SAFE LIMITS
SAFE_LIMIT_MG_L = 0.5
RECOMMENDED_MG_KG = 0.02

# Store feedback
FEEDBACK_FILE = "feedback_data.json"
ANALYSIS_HISTORY_FILE = "analysis_history.json"

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
def home():
    stats = get_statistics()
    return render_template("safety_dashboard.html", stats=stats)

@app.route("/detection-testing", methods=["GET", "POST"])
def detection_testing():
    result = None
    warning = None

    if request.method == "POST":
        try:
            sensor_value = float(request.form["sensor"])
            weight = float(request.form["weight"])

            # Calibration (demo)
            steroid_mg_l = sensor_value * 0.03

            # Safe dose calculation
            safe_dose = weight * RECOMMENDED_MG_KG

            # Safety classification
            if steroid_mg_l >= SAFE_LIMIT_MG_L:
                level = "danger"
                warning = "🚨 DANGER: Steroid level is high!"
            elif steroid_mg_l >= SAFE_LIMIT_MG_L * 0.7:
                level = "caution"
                warning = "⚠ WARNING: Steroid level nearing limit!"
            else:
                level = "safe"
                warning = "✅ SAFE: Steroid level within safe limit."

            # Ensure static folder exists
            os.makedirs("static", exist_ok=True)

            # -------- GRAPH (LINE GRAPH) --------
            x_points = list(range(1, 11))
            safe_line = [SAFE_LIMIT_MG_L] * 10
            detected_line = [steroid_mg_l * (i / 10) for i in range(1, 11)]

            plt.figure(figsize=(10, 5))
            plt.plot(
                x_points,
                safe_line,
                linewidth=2.5,
                marker="o",
                label="Safe Limit",
                color="#2e7d32"
            )

            if level == "danger":
                color = "#c62828"
                label = "Detected Level (DANGER)"
            elif level == "caution":
                color = "#f9a825"
                label = "Detected Level (WARNING)"
            else:
                color = "#66bb6a"
                label = "Detected Level (SAFE)"

            plt.plot(
                x_points,
                detected_line,
                linewidth=2.5,
                marker="s",
                label=label,
                color=color
            )

            plt.title("Steroid Level Analysis – Trend", fontweight="bold")
            plt.xlabel("Time Points")
            plt.ylabel("mg/L")
            plt.legend()
            plt.grid(True, linestyle="--", alpha=0.4)
            plt.ylim(0, max(SAFE_LIMIT_MG_L, steroid_mg_l) + 0.2)
            plt.tight_layout()
            plt.savefig("static/steroid_graph.png", dpi=150, transparent=True)
            plt.close()

            result = {
                "detected": round(steroid_mg_l, 3),
                "safe_dose": round(safe_dose, 3),
                "level": level
            }
            
            # Save to history
            analysis_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sensor_value": sensor_value,
                "weight": weight,
                "detected_level": round(steroid_mg_l, 3),
                "safe_dose": round(safe_dose, 3),
                "level": level
            }
            history = load_analysis_history()
            history.append(analysis_entry)
            save_analysis_history(history)

        except ValueError:
            warning = "❌ Invalid input. Please enter valid numbers."

    return render_template("detection_testing.html", result=result, warning=warning)

@app.route("/community-reviews", methods=["GET", "POST"])
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
            
            feedback_list = load_feedback()
            feedback_list.append(user_feedback)
            save_feedback(feedback_list)
            
            success_message = "✅ Thank you for your feedback!"
            feedback_list = load_feedback()
            return render_template("community_reviews.html", success_message=success_message, feedback_list=feedback_list)
        except Exception as e:
            error_message = f"❌ Error saving feedback: {str(e)}"
            feedback_list = load_feedback()
            return render_template("community_reviews.html", error_message=error_message, feedback_list=feedback_list)
    
    feedback_list = load_feedback()
    return render_template("community_reviews.html", feedback_list=feedback_list)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
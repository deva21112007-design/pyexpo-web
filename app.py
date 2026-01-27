from flask import Flask, render_template, request
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

# SAFE LIMITS
SAFE_LIMIT_MG_L = 0.5
RECOMMENDED_MG_KG = 0.02

@app.route("/", methods=["GET", "POST"])
def index():
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

        except ValueError:
            warning = "❌ Invalid input. Please enter valid numbers."

    return render_template("index.html", result=result, warning=warning)

if __name__ == "__main__":
    app.run(debug=True, port=5000)

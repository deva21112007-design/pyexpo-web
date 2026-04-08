"""
live_graph.py  —  Real-time terminal graph for the PureCheck and Quality Analysis
Run in a SEPARATE terminal while python app.py is running.
Press Ctrl+C to stop.
"""
import time, urllib.request, json, os, shutil, sys

URL   = "http://localhost:5000/api/sensor-stream"
DELAY = 1.5          # seconds between polls
MAX_H = 18           # chart height in rows
COLS  = 55           # chart width in chars (data bars)
history = []         # list of dicts from API

STATUS_ICONS = {"safe": "✅", "caution": "⚠️ ", "danger": "❌"}
STATUS_COLOR = {"safe": "\033[92m", "caution": "\033[93m", "danger": "\033[91m"}
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
WHITE  = "\033[97m"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def bar_char(status):
    return {"safe": "█", "caution": "▓", "danger": "▒"}.get(status, "░")

def color(status):
    return STATUS_COLOR.get(status, WHITE)

def draw(history, latest):
    term_w = shutil.get_terminal_size((80, 24)).columns
    max_val = 4.0   # sensor max display range

    clear()
    w = min(term_w - 2, 78)
    print(BOLD + CYAN + "═" * w + RESET)
    print(BOLD + CYAN + "  📊 LIVE SENSOR GRAPH  —  PureCheck and Quality Analysis" + RESET)
    print(BOLD + CYAN + "═" * w + RESET)

    # Show latest values
    if latest:
        st   = latest.get("status", "safe")
        icon = STATUS_ICONS.get(st, "")
        src  = "🔌 HARDWARE" if latest.get("source") == "hardware" else "🔵 SIMULATION"
        print(f"\n  {src}  |  {icon} {color(st)}{BOLD}{st.upper()}{RESET}")
        print(f"  Sensor : {BOLD}{latest.get('sensor_reading','--')} mg/L{RESET}"
              f"   pH : {BOLD}{latest.get('ph_value','--')}{RESET}"
              f"   Temp : {BOLD}{latest.get('temperature','--')} °C{RESET}"
              f"   Sample : {BOLD}{latest.get('sample_type','--').title()}{RESET}")
        safe_lim = latest.get('safe_limit', 0.05)
        print(f"  Safe limit : {safe_lim} mg/L\n")

    # ASCII bar chart — vertical bars, left to right
    if len(history) > 1:
        n = min(len(history), COLS)
        recent = history[-n:]

        # build rows top→bottom
        chart_lines = []
        for row in range(MAX_H, 0, -1):
            thresh = (row / MAX_H) * max_val
            line = ""
            for pt in recent:
                v = pt.get("sensor_reading", 0)
                st = pt.get("status", "safe")
                if v >= thresh:
                    line += color(st) + bar_char(st) + RESET
                else:
                    line += " "
            chart_lines.append(line)

        # y-axis labels + chart
        for i, row_line in enumerate(chart_lines):
            y_val = max_val - (i / MAX_H) * max_val
            if i % 3 == 0:
                label = f"{y_val:5.2f}│"
            else:
                label = f"     │"
            print("  " + YELLOW + label + RESET + row_line)

        # x-axis
        print("  " + YELLOW + "     └" + "─" * n + RESET)
        print("  " + YELLOW + "      " + f"← {n} readings (newest right)" + RESET)

    print("\n" + BOLD + CYAN + "═" * min(w, 78) + RESET)
    print(f"  Polling every {DELAY}s  |  Press Ctrl+C to stop")
    print(BOLD + CYAN + "═" * min(w, 78) + RESET)

latest = None
print("Connecting to localhost:5000 ...")
while True:
    try:
        with urllib.request.urlopen(URL, timeout=3) as r:
            data = json.loads(r.read())
        history.append(data)
        if len(history) > COLS:
            history.pop(0)
        latest = data
        draw(history, latest)
    except KeyboardInterrupt:
        print("\n\nStopped.")
        sys.exit(0)
    except Exception as e:
        clear()
        print(f"  ⚠️  Waiting for server... ({e})")
    time.sleep(DELAY)

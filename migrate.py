import re

with open('templates/safety_dashboard.html', 'r', encoding='utf-8') as f:
    sd_html = f.read()

# 1. Update Navigation in SD
sd_nav_replacement = '''                <li><a href="/" class="active" aria-current="page"><i class="fas fa-chart-line" aria-hidden="true"></i>
                        Safety Dashboard</a></li>
                <li><a href="/detection-testing" aria-label="Go to Detection Testing page"><i class="fas fa-flask"
                            aria-hidden="true"></i> Detection Testing</a></li>

                {% if session.user %}
                <!-- Logged In: Show Full Menu -->
                <li><a href="/community-reviews" aria-label="Go to Community Reviews page"><i class="fas fa-star"
                            aria-hidden="true"></i> Community Reviews</a></li>'''
sd_html = re.sub(
    r'<li><a href="/" class="active".*?<!-- Logged In: Show Full Menu -->.*?<li><a href="/detection-testing".*?</a></li>.*?<li><a href="/community-reviews"',
    sd_nav_replacement + '<a href="/community-reviews"',
    sd_html,
    flags=re.DOTALL
)

# 2. Extract components
ticker_match = re.search(r'(<!-- Real-Time Ticker Strip -->.*?</div>\s+</div>)', sd_html, re.DOTALL)
hw_match = re.search(r'(<!-- HARDWARE CONNECT PANEL -->.*<!-- Error / Debug Box \(shown only on error\) -->.*?</div>\s+</div>)', sd_html, re.DOTALL)
rt_match = re.search(r'(<!-- REAL-TIME MONITOR SECTION -->.*?</section>)', sd_html, re.DOTALL)
script_match = re.search(r'(<script>\s*// ============================================================\s*// REAL-TIME DATA ENGINE.*?</script>)', sd_html, re.DOTALL)

components = '\n\n'.join(filter(None, [
    ticker_match.group(1) if ticker_match else '',
    hw_match.group(1) if hw_match else '',
    rt_match.group(1) if rt_match else ''
]))
script_comp = script_match.group(1) if script_match else ''

# 3. Remove them from SD
if ticker_match: sd_html = sd_html.replace(ticker_match.group(1), '')
if hw_match: sd_html = sd_html.replace(hw_match.group(1), '')
if rt_match: sd_html = sd_html.replace(rt_match.group(1), '')
if script_match: sd_html = sd_html.replace(script_match.group(1), '')

with open('templates/safety_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(sd_html)

# ──────────────────────────────────────────
# 4. Modify Detection Testing page
with open('templates/detection_testing.html', 'r', encoding='utf-8') as f:
    dt_html = f.read()

# Make Detection Testing active in nav, and move it out of session.user
dt_nav_replacement = '''                <li><a href="/" aria-label="Go to Safety Dashboard"><i class="fas fa-chart-line" aria-hidden="true"></i>
                        Safety Dashboard</a></li>
                <li><a href="/detection-testing" class="active" aria-current="page"><i class="fas fa-flask"
                            aria-hidden="true"></i> Detection Testing</a></li>

                {% if session.user %}
                <li><a href="/community-reviews" aria-label="Go to Community Reviews page"><i class="fas fa-star"
                            aria-hidden="true"></i> Community Reviews</a></li>'''

dt_html = re.sub(
    r'<li><a href="/".*?<li><a href="/community-reviews"',
    dt_nav_replacement + '<a href="/community-reviews"',
    dt_html,
    flags=re.DOTALL
)

# Remove the old input card entirely
dt_html = re.sub(r'<!-- Input Card -->.*?</div>\s+<!-- Result Card -->', '<!-- Result Card -->', dt_html, flags=re.DOTALL)

# Insert components + New Auto-Submit button
insert_pos = dt_html.find('<!-- Result Card -->')
if insert_pos == -1: insert_pos = dt_html.find('<footer')

injection = f'''
        {components}

        <!-- HW Auto-Analyze Form -->
        <div class="card" style="text-align:center; padding: 25px; margin-top: 25px;">
            <h2 style="margin-bottom: 20px;"><i class="fas fa-microchip"></i> Hardware Sample Analysis</h2>
            <p style="margin-bottom: 20px; color: var(--tm);">Place your sample on the sensor. When the live waveform stabilizes, click below to run the official analysis.</p>
            
            <form id="hw-analysis-form" method="post" action="/detection-testing">
                <input type="hidden" id="live_sample" name="sample_type" value="milk">
                <input type="hidden" id="live_sensor" name="sensor" value="">
                <input type="hidden" id="live_weight" name="weight" value="1.0">
                
                <button type="button" class="btn-primary btn-large" onclick="submitLiveAnalysis()" style="font-size: 1.2rem; padding: 15px 30px; box-shadow: 0 4px 15px rgba(0, 191, 165, 0.4);">
                    <i class="fas fa-play-circle"></i> Analyze Current Hardware Sample
                </button>
            </form>
            <div id="hw-submit-msg" style="margin-top: 15px; font-weight: 600; color: #00bfa5; display: none;">Capturing live data...</div>
        </div>

'''
dt_html = dt_html[:insert_pos] + injection + dt_html[insert_pos:]

submit_fn = '''
        function submitLiveAnalysis() {
            if (typeof waveformData !== "undefined" && waveformData.length > 0) {
                const latest = waveformData[waveformData.length - 1];
                document.getElementById('live_sensor').value = latest.val;
            } else {
                const sVal = document.getElementById('rt-sensor-val').textContent.split(' ')[0];
                document.getElementById('live_sensor').value = isNaN(parseFloat(sVal)) ? 0 : parseFloat(sVal);
            }
            
            const sampleText = document.getElementById('rt-sample-label').textContent.toLowerCase();
            if (sampleText.includes('meat')) document.getElementById('live_sample').value = 'meat';
            else if (sampleText.includes('water')) document.getElementById('live_sample').value = 'water';
            else document.getElementById('live_sample').value = 'milk';
            
            document.getElementById('hw-submit-msg').style.display = 'block';
            document.getElementById('hw-analysis-form').submit();
        }
'''

if '</body>' in dt_html:
    dt_html = dt_html.replace('</body>', f'{script_comp}\\n<script>\\n{submit_fn}\\n</script>\\n</body>')
else:
    dt_html += f'{script_comp}\\n<script>\\n{submit_fn}\\n</script>\\n</body>'

with open('templates/detection_testing.html', 'w', encoding='utf-8') as f:
    f.write(dt_html)

print('SUCCESS')

// =====================================================
//  STEROID DETECTION SYSTEM — ESP32 Sensor Node
// =====================================================
//  Sensors:
//    - pH Sensor Module  --> GPIO 34 (ADC1_CH6)
//    - LM35 Temperature  --> GPIO 35 (ADC1_CH7)
//
//  Wiring:
//    pH Module:
//      VCC → 3.3V or 5V (Check module spec, logic out must be <= 3.3V, use divider if needed)
//      GND → GND
//      PO  → 34
//
//    LM35:
//      VCC → 3.3V or 5V
//      GND → GND
//      OUT → 35
//
//  Output: JSON over Serial at 115200 baud, every 1 second
//  Format: {"ph":6.87,"temp":24.5,"tds":300,"turbidity":2.5,"color":1,"sensor":2.14,"status":"ok"}
// =====================================================

const int PH_PIN        = 34;   // pH sensor analog output (ESP32 ADC1)
const int TEMP_PIN      = 35;   // LM35 analog output (ESP32 ADC1)
const int TDS_PIN       = 32;   // TDS sensor analog output
const int TURBIDITY_PIN = 33;   // Turbidity sensor analog output
const int COLOR_PIN     = 25;   // Color sensor analog logic/output

// pH Calibration offset (adjust if readings are off)
// Measure known pH 7.0 buffer and set offset accordingly
float phCalibrationOffset = 0.0;

// Send interval
const unsigned long SEND_INTERVAL = 1000; // ms
unsigned long lastSendTime = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }  // Wait for Serial on some boards
    
    // Short boot delay for sensor stabilization
    delay(500);
    
    // Send a startup message
    Serial.println("{\"status\":\"boot\",\"msg\":\"Sensor Node Ready\"}");
}

void loop() {
    unsigned long now = millis();
    if (now - lastSendTime < SEND_INTERVAL) return;
    lastSendTime = now;

    // ── Read pH (10-sample average for stability) ──────────
    long phRawSum = 0;
    for (int i = 0; i < 10; i++) {
        phRawSum += analogRead(PH_PIN);
        delay(10);
    }
    int phRaw = phRawSum / 10;

    // Convert raw ADC to voltage (ESP32: 3.3V reference, 12-bit ADC max 4095)
    float phVoltage = phRaw * (3.3 / 4095.0);

    // Convert voltage to pH
    // Standard formula for most pH modules:
    //   pH = 7 + (midVoltage - voltage) / slope
    //   midVoltage ≈ 2.5V, slope ≈ 0.18 V/pH unit
    float phValue = 7.0 + ((2.5 - phVoltage) / 0.18) + phCalibrationOffset;
    phValue = constrain(phValue, 0.0, 14.0);

    // ── Read Temperature (LM35) ────────────────────────────
    int tempRaw = analogRead(TEMP_PIN);
    float tempVoltage = tempRaw * (3.3 / 4095.0);
    // LM35: 10 mV per °C, so temp = voltage * 100
    float temperature = tempVoltage * 100.0;

    // ── Read TDS (Total Dissolved Solids) ──────────────────
    int tdsRaw = analogRead(TDS_PIN);
    float tdsVoltage = tdsRaw * (3.3 / 4095.0);
    // Rough approximation formula for standard analog TDS meter
    float tdsValue = (133.42 * pow(tdsVoltage, 3) - 255.86 * pow(tdsVoltage, 2) + 857.39 * tdsVoltage) * 0.5;
    tdsValue = max(0.0f, tdsValue); // prevent negative

    // ── Read Turbidity ─────────────────────────────────────
    int turbRaw = analogRead(TURBIDITY_PIN);
    float turbVoltage = turbRaw * (3.3 / 4095.0);
    // Approximation: 0-3.3V mapped roughly to 0-3000 NTU (varies heavily by sensor)
    float turbidityValue = map(turbRaw, 0, 4095, 3000, 0); 
    turbidityValue = constrain(turbidityValue, 0.0, 3000.0);

    // ── Read Colour ────────────────────────────────────────
    // For a complex I2C color sensor (like TCS3200), this would be digital.
    // Assuming simple analog proxy for demonstration: 0-4095 mapped.
    int colorRaw = analogRead(COLOR_PIN);
    // Let's pass the raw 12-bit value to let the backend interpret "milk whiteness"
    int colorValue = colorRaw;

    // ── Derive Sensor Reading for Steroid Detection ────────
    // Steroid contamination in milk typically lowers pH (more acidic).
    // We map pH deviation below neutral (7.0) to a mg/L steroid proxy.
    // Safe pH for fresh milk: 6.4 – 6.8
    // This sensor_reading feeds directly into the Flask detection formula.
    float sensorReading = max(0.0, (7.5 - phValue) * 1.2 + 0.3);
    sensorReading = constrain(sensorReading, 0.1, 5.0);

    // ── Build + Send JSON ──────────────────────────────────
    Serial.print("{");
    Serial.print("\"ph\":");        Serial.print(phValue, 2);
    Serial.print(",\"temp\":");     Serial.print(temperature, 1);
    Serial.print(",\"tds\":");      Serial.print(tdsValue, 0);
    Serial.print(",\"turbidity\":");Serial.print(turbidityValue, 0);
    Serial.print(",\"color\":");    Serial.print(colorValue);
    Serial.print(",\"sensor\":");   Serial.print(sensorReading, 2);
    Serial.print(",\"raw_ph\":");   Serial.print(phRaw);
    Serial.print(",\"status\":\"ok\"");
    Serial.println("}");
}

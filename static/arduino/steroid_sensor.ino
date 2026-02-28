// =====================================================
//  STEROID DETECTION SYSTEM — Arduino Uno Sensor Node
// =====================================================
//  Sensors:
//    - pH Sensor Module  --> Analog Pin A0
//    - LM35 Temperature  --> Analog Pin A1
//
//  Wiring:
//    pH Module:
//      VCC → 5V
//      GND → GND
//      PO  → A0
//
//    LM35:
//      VCC → 5V
//      GND → GND
//      OUT → A1
//
//  Output: JSON over Serial at 9600 baud, every 1 second
//  Format: {"ph":6.87,"temp":24.5,"sensor":2.14,"status":"ok"}
// =====================================================

const int PH_PIN   = A0;   // pH sensor analog output
const int TEMP_PIN = A1;   // LM35 analog output

// pH Calibration offset (adjust if readings are off)
// Measure known pH 7.0 buffer and set offset accordingly
float phCalibrationOffset = 0.0;

// Send interval
const unsigned long SEND_INTERVAL = 1000; // ms
unsigned long lastSendTime = 0;

void setup() {
    Serial.begin(9600);
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

    // Convert raw ADC to voltage (5V reference, 10-bit ADC)
    float phVoltage = phRaw * (5.0 / 1023.0);

    // Convert voltage to pH
    // Standard formula for most pH modules:
    //   pH = 7 + (midVoltage - voltage) / slope
    //   midVoltage ≈ 2.5V, slope ≈ 0.18 V/pH unit
    float phValue = 7.0 + ((2.5 - phVoltage) / 0.18) + phCalibrationOffset;
    phValue = constrain(phValue, 0.0, 14.0);

    // ── Read Temperature (LM35) ────────────────────────────
    int tempRaw = analogRead(TEMP_PIN);
    float tempVoltage = tempRaw * (5.0 / 1023.0);
    // LM35: 10 mV per °C, so temp = voltage * 100
    float temperature = tempVoltage * 100.0;

    // ── Derive Sensor Reading for Steroid Detection ────────
    // Steroid contamination in milk typically lowers pH (more acidic).
    // We map pH deviation below neutral (7.0) to a mg/L steroid proxy.
    // Safe pH for fresh milk: 6.4 – 6.8
    // This sensor_reading feeds directly into the Flask detection formula.
    float sensorReading = max(0.0, (7.5 - phValue) * 1.2 + 0.3);
    sensorReading = constrain(sensorReading, 0.1, 5.0);

    // ── Build + Send JSON ──────────────────────────────────
    Serial.print("{");
    Serial.print("\"ph\":");      Serial.print(phValue, 2);
    Serial.print(",\"temp\":");   Serial.print(temperature, 1);
    Serial.print(",\"sensor\":"); Serial.print(sensorReading, 2);
    Serial.print(",\"raw_ph\":"); Serial.print(phRaw);
    Serial.print(",\"status\":\"ok\"");
    Serial.println("}");
}

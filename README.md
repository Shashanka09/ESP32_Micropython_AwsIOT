
# ESP32 + DHT11 + AWS IoT Core (MicroPython)

## Project Overview
This project reads temperature and humidity from a **DHT11** sensor connected to an **ESP32** running MicroPython and securely publishes the data to **AWS IoT Core** using MQTT with mutual TLS (X.509) certificates.

> **Note:** The actual MicroPython code file (Python script) is intentionally excluded from this document. Put your code file in a separate folder (e.g., `code/`) in your repo.

---

## Files (place in repository root or appropriate folders)
- `aws_dht_publish.py` — (your MicroPython script file — keep in `code/`)
- `certificate.pem.crt` — device certificate (upload to device filesystem)
- `private.pem.key` — device private key (upload to device filesystem)
- `AmazonRootCA1.pem` — Amazon Root CA (upload to device filesystem)
- `ESP32_DHT_AWS_Readme.docx` — (this document)
- `circuit_diagram.png` — wiring diagram image

---

## Hardware Components
- ESP32 development board (any common dev board with MicroPython support)
- DHT11 temperature & humidity sensor
- Jumper wires
- USB cable for power & programming

### Wiring (connections)
- **DHT11 VCC** → **ESP32 3V3**
- **DHT11 GND** → **ESP32 GND**
- **DHT11 DATA** → **ESP32 GPIO4** (configurable in code)

(If you use a different GPIO, update the code's `pin_number` accordingly.)

---

## Circuit Diagram
See the included `circuit_diagram.png` image in the repo for a simple schematic. It shows the ESP32, DHT11 and the VCC/GND/DATA connections. Use this as a reference when wiring your hardware.

---

## AWS IoT Setup (step-by-step)
1. Sign in to the AWS Console and open **IoT Core**.
2. Create a **Thing** (name example: `myESP32`). Optionally create a thing type or group if you have many devices.
3. Create and download device credentials when creating the Thing:
   - Device certificate (e.g. `certificate.pem.crt`)
   - Private key (e.g. `private.pem.key`)
   - Root CA certificate (download Amazon root CA; e.g. `AmazonRootCA1.pem`)
4. Create an **IoT policy** with permissions at minimum:
   - `iot:Connect`
   - `iot:Publish`
   - `iot:Subscribe`
   - `iot:Receive`
   Scope the policy to your topic or allow `devices/*` during testing.
5. Attach the policy to your certificate, and attach the certificate to the Thing.
6. In **IoT Core → Settings**, copy your **Device data endpoint**. It looks like:
   `abcdefghijklmnop-ats.iot.<region>.amazonaws.com`
   > **Important:** Use this endpoint as your MQTT server — do **not** use the ARN (aws resource name).

---

## Preparing and Uploading Certificates to the ESP32
1. Ensure the certificate and key files are PEM-format text files. Open them on your PC to verify they start with `-----BEGIN CERTIFICATE-----` / `-----BEGIN PRIVATE KEY-----`.
2. Using Thonny, ampy, mpremote, or WebREPL, upload the three files to the ESP32 filesystem (root directory):
   - `AmazonRootCA1.pem`
   - `certificate.pem.crt`
   - `private.pem.key`
3. Confirm the files are present by opening the MicroPython REPL and running `import os; print(os.listdir())`.

---

## MicroPython / Firmware Recommendations
- Use a MicroPython build for ESP32 with working SSL/TLS (mbedTLS). Some minimal builds lack full TLS support required by AWS IoT.
- If you experience TLS handshake errors, consider flashing an official or custom build with full SSL support.
- Keep PEM files small and filenames exact (case sensitive).

---

## Where to Configure Values (in your code)
Open your MicroPython script and set these variables (names may vary depending on your code):
- `WIFI_SSID` — your Wi-Fi network name
- `WIFI_PASS` — Wi-Fi password
- `AWS_ENDPOINT` — AWS IoT Device data endpoint (not ARN)
- `THING_NAME` — e.g., `myESP32`
- `DEVICE_CERT` — filename on device (e.g., `/certificate.pem.crt`)
- `DEVICE_KEY` — filename on device (e.g., `/private.pem.key`)
- `CLIENT_CA` or `ROOT_CA` — filename on device (e.g., `/AmazonRootCA1.pem`)
- `MQTT_TOPIC` — topic your device publishes to (for example: `devices/myESP32/telemetry`)

---

## How to Upload & Run (high-level)
1. Flash MicroPython to your ESP32 (follow official docs for your board).
2. Upload the MicroPython script (e.g., `aws_dht_publish.py`) to the board using Thonny or `ampy`/`mpremote`.
3. Upload the three PEM files to the device filesystem.
4. From the REPL or Thonny run the script (or set it as `main.py`/`boot.py` if you want it to run automatically on boot).
5. Monitor the REPL output — it should show Wi-Fi connection, MQTT connect success, and published JSON payloads every interval.

---

## Testing & Verification (AWS Console)
1. Open **AWS IoT Core → MQTT test client**.
2. Subscribe to the device topic you configured (example):
   - `devices/myESP32/telemetry` (exact device output)
   - or wildcard test: `devices/#` (all devices under `devices/`)
   - or `devices/+/telemetry` (all devices' telemetry)
3. You should see JSON messages arriving when the device publishes.

---

## Troubleshooting (common problems & fixes)
- **TLS / SSL handshake errors (e.g., negative return codes like -202)**:
  - Ensure you used the AWS IoT **endpoint URL** (not ARN).
  - Confirm certificate/key file names and that they are uploaded to the device filesystem.
  - Ensure your MicroPython firmware supports TLS client certs (some builds do not).
- **Publish fails intermittently**:
  - Check Wi-Fi signal/credentials and reconnection logic in code.
  - Add retries and exponential backoff if required.
- **DHT sensor read errors**:
  - DHT11 is slow and sometimes returns errors; add try/except with small delay between retries.
- **Permissions errors in AWS**:
  - Verify the IoT policy attached to the certificate allows `iot:Publish`/`Connect` for your topic.
- **File not found on device**:
  - Filenames are case-sensitive — confirm with `os.listdir()` on the device.

---

## Final Output / Evidence (placeholder)
Create a folder named `output/` in your repo and place the following screenshots or files there:
- `screenshot_repl.png` — REPL showing "MQTT connected" and "Published OK"
- `screenshot_aws_mqtt_client.png` — AWS IoT MQTT test client showing incoming messages
- `screenshot_files.png` — `os.listdir()` output showing certificate files on the device
- `screenshot_wlan.png` — `ifconfig()` output or Wi-Fi connection evidence

In your README (or GitHub release), reference these images:
- `output/screenshot_repl.png`
- `output/screenshot_aws_mqtt_client.png`
- `output/screenshot_files.png`

---

## Topics & Wildcards (quick reminder)
- Exact topic: `devices/myESP32/telemetry`
- Single level wildcard: `devices/+/telemetry`
- Multi level wildcard: `devices/#`

---

## License
MIT License 

---

## Author / Contact
Shashanka Shekhar Chakraborty 

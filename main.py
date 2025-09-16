# aws_dht_publish.py
# Read DHT11 and publish to AWS IoT using MQTT (mutual TLS).
# Timer signals the main loop to measure & publish (no blocking ops in IRQ).

import time
import json
import machine
from machine import Pin, Timer
import dht
import ubinascii
import usocket as socket
import network
from umqtt.simple import MQTTClient  # or umqtt.robust if you have it

# ------------------ CONFIG ------------------
WIFI_SSID = "wifi name"
WIFI_PASS = "wifi password"

AWS_ENDPOINT = "Your end point url"   # e.g. abcdefghijklmnop-ats.iot.us-east-1.amazonaws.com
AWS_PORT = 8883

CLIENT_CERT = "/AmazonRootCA1.pem"     # server CA (optional for some setups)
                                      # library we're using, AWS root CA certificate not in use, read library doc if you're using a different library
DEVICE_CERT = "/certificate.pem.crt" #Client certificate
                                    #Upload it to the micropython device
DEVICE_KEY  = "/private.pem.key" #Privet key
                                 #Upload it to the micropython device

THING_NAME = "Your thing name"    # client id / thing name
                                 # You'll find it in : In AWS Console → IoT Core → Settings (bottom-left) → Device data endpoint
MQTT_TOPIC = "devices/{}/telemetry".format(THING_NAME)

MEASURE_INTERVAL_MS = 5000   # measurement period (ms)

# ------------------ GLOBALS ------------------
pin_number = 4                # DHT data pin (GPIO number)
measure_pending = False       # set by timer, read by main loop
last_measure_time = 0
wifi_connected = False
mqtt_client = None

# ------------------ UTILITIES ------------------
def connect_wifi():
    global wifi_connected
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASS)
        timeout = 15  # seconds
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("WiFi connect timed out")
                wifi_connected = False
                return False
            time.sleep(0.5)
    wifi_connected = True
    print("WiFi connected, IP:", wlan.ifconfig()[0])
    return True

def make_mqtt_client():
    """
    Returns an MQTTClient configured for TLS mutual auth.
    Note: MicroPython SSL support and MQTTClient ssl_params vary by build.
    """
    client_id = ubinascii.hexlify(machine.unique_id()).decode()  # unique client id
    # Create client. umqtt.simple's constructor signature:
    # MQTTClient(client_id, server, port=0, user=None, password=None,
    #            keepalive=0, ssl=False, ssl_params=None)
    ssl_params = {
        "key": DEVICE_KEY,        # some builds expect 'key' and 'cert' or 'certfile'
        "cert": DEVICE_CERT,
        "server_side": False,
        #"ca_certs": CLIENT_CERT   # try including CA file name if needed
    }
    client = MQTTClient(client_id=client_id,
                        server=AWS_ENDPOINT,
                        port=AWS_PORT,
                        keepalive=60,
                        ssl=True,
                        ssl_params=ssl_params)
    return client

def mqtt_connect():
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = make_mqtt_client()
    try:
        print("Connecting to AWS IoT MQTT...")
        mqtt_client.connect()
        print("MQTT connected")
        return True
    except Exception as e:
        print("MQTT connection failed:", e)
        mqtt_client = None
        return False

def mqtt_publish(payload):
    global mqtt_client
    if mqtt_client is None:
        if not mqtt_connect():
            return False
    try:
        mqtt_client.publish(MQTT_TOPIC, payload)
        return True
    except Exception as e:
        print("Publish failed, will try reconnect:", e)
        try:
            mqtt_client.disconnect()
        except Exception:
            pass
        mqtt_client = None
        return False

# ------------------ SENSOR ------------------
dht_sensor = dht.DHT11(Pin(pin_number))

def measure_and_publish():
    """
    Perform a DHT measurement and publish JSON to AWS.
    This function runs in the main loop, NOT in timer callback.
    """
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
    except Exception as e:
        print("Sensor read failed:", e)
        return False

    payload = {
        "thing": THING_NAME,
        "timestamp": time.time(),
        "temperature_C": temp,
        "humidity_pct": hum
    }
    payload_json = json.dumps(payload)
    print("Publishing:", payload_json)

    if mqtt_publish(payload_json):
        print("Published OK")
        return True
    else:
        print("Publish failed")
        return False

# ------------------ TIMER CALLBACK (very small / safe) ------------------
def timer_callback(t):
    # **VERY IMPORTANT**: keep this tiny and non-blocking.
    # Set a flag for the main loop to handle the measurement & network.
    global measure_pending
    measure_pending = True

# ------------------ MAIN ------------------
def main():
    global measure_pending, last_measure_time, mqtt_client

    # Connect to WiFi first
    if not connect_wifi():
        print("Cannot continue without WiFi. Rebooting in 10s.")
        time.sleep(10)
        machine.reset()

    # Create and start timer (only sets flag)
    tm = Timer(1)
    tm.init(period=MEASURE_INTERVAL_MS, mode=Timer.PERIODIC, callback=timer_callback)
    print("Timer started, measuring every {} ms".format(MEASURE_INTERVAL_MS))

    # Try initial MQTT connect (best-effort)
    mqtt_connect()

    # Main event loop
    try:
        while True:
            if measure_pending:
                measure_pending = False
                last_measure_time = time.time()
                # Do the actual sensor reading and publishing here (blocking ok)
                success = measure_and_publish()
                # optionally: if publish failed, try reconnect/backoff logic (simple example)
                if not success:
                    print("Attempting reconnect in 5s...")
                    time.sleep(5)
                    mqtt_connect()
            # do other non-blocking tasks here
            time.sleep_ms(100)
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        try:
            tm.deinit()
        except Exception:
            pass
        try:
            if mqtt_client:
                mqtt_client.disconnect()
        except Exception:
            pass

# Run main when module executed
if __name__ == "__main__":
    main()


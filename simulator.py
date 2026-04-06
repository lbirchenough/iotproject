"""
simulator.py — pretends to be the ESP8266, publishing sensor data to AWS IoT Core.
Publishes to the same topics and payload format as the real device.
"""

import json
import time
import random
import ssl
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
# --- CONFIG ---
AWS_ENDPOINT  = "a38kgyfs1sv13m-ats.iot.ap-southeast-2.amazonaws.com"
CERT_FILE     = "certs/5f2415de5fd85942e566713f8e5cefde4ba2c6eb5f4db687c25fa049bb8f33c4-certificate.pem.crt"
KEY_FILE      = "certs/5f2415de5fd85942e566713f8e5cefde4ba2c6eb5f4db687c25fa049bb8f33c4-private.pem.key"
AWS_PORT      = 8883
CLIENT_ID     = "esp8266-box1"

TOPIC_DISTANCE = "esp8266/box1/distance"
TOPIC_SWITCH   = "esp8266/box1/switch"

PUBLISH_EVERY  = 30  # seconds


# --- CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[MQTT] Connected to AWS IoT Core")
    else:
        print("[MQTT] Connection failed, rc=", rc)

def on_publish(client, userdata, mid, rc=None, properties=None):
    print("[MQTT] Publish confirmed, mid=", mid)


# --- SIMULATED SENSOR READS ---
def read_distance():
    """Simulate SHARP sensor: random value 10-80cm."""
    return round(random.uniform(10, 80), 1)

def read_switch():
    """Simulate switch: active (1) roughly 1 in 10 times, open (0) otherwise."""
    return 1 if random.random() < 0.2 else 0


# --- MAIN ---
client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_publish = on_publish

tls_ctx = ssl.create_default_context()
tls_ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
tls_ctx.check_hostname = False
tls_ctx.verify_mode = ssl.CERT_NONE  # matches ESP8266 behaviour — no server cert verification

client.tls_set_context(tls_ctx)
client.connect(AWS_ENDPOINT, AWS_PORT)
client.loop_start()

print(f"[Sim] Publishing every {PUBLISH_EVERY}s. Ctrl+C to stop.\n")

try:
    while True:
        distance = read_distance()
        switch   = read_switch()

        measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        distance_payload = json.dumps({
            "device_id": "esp8266-box1",
            "sensor_type": "distance",
            "value": distance,
            "unit": "cm",
            "measured_at": measured_at
        })

        switch_payload = json.dumps({
            "device_id": "esp8266-box1",
            "sensor_type": "switch",
            "value": switch,
            "unit": "binary",
            "measured_at": measured_at
        })

        client.publish(TOPIC_DISTANCE, distance_payload)
        print(f"[Sent] {TOPIC_DISTANCE}: {distance_payload}")

        client.publish(TOPIC_SWITCH, switch_payload)
        print(f"[Sent] {TOPIC_SWITCH}: {switch_payload}")

        time.sleep(PUBLISH_EVERY)

except KeyboardInterrupt:
    print("\n[Sim] Stopped.")
    client.loop_stop()
    client.disconnect()

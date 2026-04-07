"""
simulator.py — pretends to be the ESP8266, publishing sensor data to AWS IoT Core.
Publishes to the same topics and payload format as the real device.

Usage: python simulator.py <box-id>
  e.g. python simulator.py box1
       python simulator.py box2
"""

import json
import sys
import time
import random
import ssl
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# --- ARG ---
if len(sys.argv) != 2:
    print("Usage: python simulator.py <box-id>  (e.g. box1, box2)")
    sys.exit(1)

BOX_ID = sys.argv[1]  # e.g. "box1"

# --- CONFIG ---
AWS_ENDPOINT   = "a38kgyfs1sv13m-ats.iot.ap-southeast-2.amazonaws.com"

import glob
_cert_dir = f"certs/{BOX_ID}"
_certs = glob.glob(f"{_cert_dir}/*-certificate.pem.crt")
_keys  = glob.glob(f"{_cert_dir}/*-private.pem.key")
if not _certs or not _keys:
    print(f"[Error] Could not find cert/key in {_cert_dir}/")
    print("  Expected: <id>-certificate.pem.crt and <id>-private.pem.key")
    sys.exit(1)
CERT_FILE = _certs[0]
KEY_FILE  = _keys[0]
print(f"[Certs] Using cert: {CERT_FILE}")
print(f"[Certs] Using key:  {KEY_FILE}")
AWS_PORT       = 8883
CLIENT_ID      = f"esp8266-{BOX_ID}"

TOPIC_DISTANCE = f"esp8266/{BOX_ID}/distance"
TOPIC_SWITCH   = f"esp8266/{BOX_ID}/switch"

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

print(f"[Sim] {CLIENT_ID} publishing every {PUBLISH_EVERY}s. Ctrl+C to stop.\n")

try:
    while True:
        distance = read_distance()
        switch   = read_switch()

        measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        distance_payload = json.dumps({
            "device_id": CLIENT_ID,
            "sensor_type": "distance",
            "value": distance,
            "unit": "cm",
            "measured_at": measured_at
        })

        switch_payload = json.dumps({
            "device_id": CLIENT_ID,
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

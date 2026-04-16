"""
simulator.py — pretends to be the ESP8266, publishing sensor data to AWS IoT Core.
Publishes to the same topics and payload format as the real device.

Usage: python simulator.py <box-id> [-laravel]
  e.g. python simulator/simulator.py box1
       python simulator/simulator.py box2 -laravel
"""

import argparse
import json
import os
import sys
import time
import random
import ssl
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Add parent directory to path for shared config imports (local: ../terraform_config.py, Docker: ./terraform_config.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from terraform_config import AWS_ENDPOINT

# --- ARGS ---
parser = argparse.ArgumentParser(description="IoT sensor simulator for AWS IoT Core")
parser.add_argument("box_id", help="Box identifier (e.g. box1, box2)")
parser.add_argument("-laravel", action="store_true", help="Also post data to the Laravel backend")
args = parser.parse_args()

# --- CONFIG ---
BOX_ID         = args.box_id
BOX_NUM        = int(''.join(filter(str.isdigit, BOX_ID)))
AWS_PORT       = 8883
CLIENT_ID      = f"iot_{BOX_ID}"
_base          = os.path.dirname(os.path.abspath(__file__))
_certs_dir     = os.path.join(_base, "..", "certs") if os.path.isdir(os.path.join(_base, "..", "certs")) else os.path.join(_base, "certs")
CERT_FILE      = os.path.join(_certs_dir, f"iot_{BOX_ID}.pem")
KEY_FILE       = os.path.join(_certs_dir, f"iot_{BOX_ID}.key")
TOPIC_DISTANCE = f"iot_{BOX_ID}/distance"
TOPIC_SWITCH   = f"iot_{BOX_ID}/switch"
PUBLISH_EVERY  = 30  # seconds
LARAVEL_URL    = "https://livewire-test-8riau887.on-forge.com/api/sensor-data"

if args.laravel:
    import requests
    try:
        API_KEY = os.environ["API_KEY"]
    except KeyError:
        from config import API_KEY

if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
    print(f"[Error] Could not find cert/key:")
    print(f"  Expected: {CERT_FILE} and {KEY_FILE}")
    sys.exit(1)
print(f"[Certs] Using cert: {CERT_FILE}")
print(f"[Certs] Using key:  {KEY_FILE}")


# --- CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[MQTT] Connected to AWS IoT Core")
    else:
        print("[MQTT] Connection failed, rc=", rc)

def on_publish(client, userdata, mid, rc=None, properties=None):
    print("[MQTT] Publish confirmed, mid=", mid)


# --- LARAVEL POST ---

def post_to_laravel(sensor_id, value, unit, sensor_type):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        resp = requests.post(
            LARAVEL_URL,
            json={"sensor_name": sensor_id, "value": value, "unit": unit, "type": sensor_type, "time": timestamp},
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
            timeout=10
        )
        if resp.status_code in (200, 201):
            print(f"[Laravel] OK {sensor_type}={value}{unit} HTTP {resp.status_code}")
        else:
            print(f"[Laravel] FAIL HTTP {resp.status_code}")
    except Exception as e:
        print(f"[Laravel] ERROR: {e}")


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

        if args.laravel:
            post_to_laravel(BOX_NUM, distance, "cm", "distance")
            post_to_laravel(BOX_NUM, switch, "binary", "switch")

        time.sleep(PUBLISH_EVERY)

except KeyboardInterrupt:
    print("\n[Sim] Stopped.")
    client.loop_stop()
    client.disconnect()

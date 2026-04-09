import time
import network
import ntptime
import ujson
import gc
import machine
import ssl
import socket
from umqtt.simple import MQTTClient
from config import SSID, PASSWORD, API_KEY

# --- SAFETY DELAY (mpremote "Insurance Policy") ---
print("[System] Booting in 5s... Press Ctrl+C now to intercept.")
time.sleep(5)

# --- CONFIGURATION ---
aws_endpoint   = b"a38kgyfs1sv13m-ats.iot.ap-southeast-2.amazonaws.com"
client_id      = b"esp8266-box1"
TOPIC_DISTANCE = b"esp8266/box1/distance"
TOPIC_SWITCH   = b"esp8266/box1/switch"
DEVICE_ID      = "esp8266-box1"
UTC_OFFSET_S   = 8 * 3600
PUBLISH_EVERY  = 30   # seconds between sensor reads/publishes
API_HOST       = "livewire-test-8riau887.on-forge.com"
API_PATH       = "/api/sensor-data"
API_PORT       = 443

# Set True if your breakout board has a built-in ADC voltage divider.
# D1 Mini and most ESP-12E breakout boards include this (safe input: 0-3.2V).
BOARD_HAS_ADC_DIVIDER = True

# Number of ADC samples to average per reading (reduces SHARP sensor noise)
ADC_SAMPLES = 5

# ADC raw value below which the sensor is considered disconnected/floating.
# Floating A0 on a D1 Mini reads 0-15. Connected SHARP reads 80+ at max range.
ADC_MIN_CONNECTED = 20

# --- PIN SETUP ---
adc    = machine.ADC(0)
switch = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)  # D2 / GPIO4


# --- SENSOR READERS ---

def read_sharp_distance_cm():
    """
    Read SHARP 2Y0A21 IR distance sensor from A0.
    Returns: (distance_cm, None) on valid reading
             (None, reason_string) on invalid/disconnected
    """
    raw_sum = 0
    for _ in range(ADC_SAMPLES):
        raw_sum += adc.read()
        time.sleep_ms(2)
    raw = raw_sum / ADC_SAMPLES  # 0-1023

    if raw < ADC_MIN_CONNECTED:
        return None, "sensor disconnected (ADC raw={:.0f})".format(raw)

    if BOARD_HAS_ADC_DIVIDER:
        voltage = raw / 1023.0 * 3.2
    else:
        voltage = raw / 1023.0 * 1.0

    if voltage < 0.1:
        return None, "voltage too low ({:.2f}V)".format(voltage)

    distance = 27.728 * (voltage ** -1.2045)  # SHARP 2Y0A21 empirical formula

    if distance < 10:
        return None, "object too close (<10cm)"
    if distance > 80:
        return None, "out of range (>80cm)"

    return round(distance, 1), None


def read_switch():
    """
    Read D2 (GPIO4) with internal pull-up.
    Returns 1 = switch closed (active), 0 = switch open
    """
    return 1 if switch.value() == 0 else 0


def get_timestamp():
    """Return current time as ISO 8601 UTC string using NTP-synced RTC."""
    t = time.localtime(time.time() + UTC_OFFSET_S)
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


# --- WIFI ---

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("[WiFi] Connecting...")
        wlan.connect(SSID, PASSWORD)
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(0.5)

    if wlan.isconnected():
        ip, subnet, gateway, _ = wlan.ifconfig()
        wlan.ifconfig((ip, subnet, gateway, '8.8.8.8'))  # force Google DNS
        print("[WiFi] Connected! IP:", wlan.ifconfig()[0])
        gc.collect()
        return True

    print("[WiFi] Failed to connect.")
    return False


def sync_ntp():
    try:
        ntptime.settime()
        print("[NTP] Time synced.")
    except:
        print("[NTP] Sync failed - timestamps may be inaccurate.")
    gc.collect()


# --- MQTT ---

def mqtt_connect():
    print("[MQTT] Connecting to AWS (SSL handshake - this takes ~10-30s)...")

    # ESP8266 MicroPython uses axTLS which only supports PKCS#1 format keys.
    # Modern OpenSSL generates PKCS#8 by default which axTLS rejects with OSError -2.
    # Certs and keys must be converted to PKCS#1 DER format before uploading to the board:
    #   openssl rsa -inform PEM -outform DER -traditional -in private.pem.key -out private.pem.key
    #   openssl x509 -in cert.pem.crt -out cert.pem.crt -outform DER
    # See: https://github.com/orgs/micropython/discussions/18794
    with open("cert.pem.crt", "rb") as f:
        cert = f.read()
    with open("private.pem.key", "rb") as f:
        key = f.read()

    ssl_params = {"key": key, "cert": cert, "server_side": False}

    client = MQTTClient(
        client_id,
        aws_endpoint,
        port=8883,
        ssl=True,
        ssl_params=ssl_params,
    )
    client.connect()

    del cert, key  # free large cert bytes from RAM immediately
    gc.collect()

    print("[MQTT] Connected.")
    return client


def publish_to_aws(mqtt_client, topic, payload_dict):
    """Publish a dict payload to an MQTT topic. Resets mqtt on failure."""
    try:
        mqtt_client.publish(topic, ujson.dumps(payload_dict))
        print("[MQTT] Sent to", topic, payload_dict)
        return True
    except Exception as e:
        print("[MQTT] Publish failed:", e)
        return False


# --- LARAVEL HTTPS POST ---

def post_to_laravel(sensor_id, value, unit, sensor_type):
    """
    POST a sensor reading to the Laravel API over HTTPS.
    Returns True on HTTP 200/201, False on failure.
    """
    t = time.localtime(time.time() + UTC_OFFSET_S)
    timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )

    body = '{{"sensor_name":{},"value":{},"unit":"{}","type":"{}","time":"{}"}}'.format(
        sensor_id, value, unit, sensor_type, timestamp
    )

    request = (
        "POST {} HTTP/1.1\r\n"
        "Host: {}\r\n"
        "X-API-Key: {}\r\n"
        "Content-Type: application/json\r\n"
        "Accept: application/json\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n"
        "\r\n"
        "{}"
    ).format(API_PATH, API_HOST, API_KEY, len(body), body)

    sock = None
    ssl_sock = None
    try:
        addr     = socket.getaddrinfo(API_HOST, API_PORT)[0][-1]
        sock     = socket.socket()
        sock.settimeout(15)
        sock.connect(addr)
        ssl_sock = ssl.wrap_socket(sock, server_hostname=API_HOST)
        ssl_sock.write(request.encode())

        response = b""
        while True:
            chunk = ssl_sock.read(256)
            if not chunk:
                break
            response += chunk
            if b"\r\n\r\n" in response:
                break

        status_code = int(response.decode("utf-8", "ignore").split("\r\n")[0].split(" ")[1])
        if status_code in (200, 201):
            print("[Laravel] OK {}={}{} HTTP {}".format(sensor_type, value, unit, status_code))
            return True
        else:
            print("[Laravel] FAIL HTTP {}".format(status_code))
            return False

    except Exception as e:
        print("[Laravel] ERROR:", e)
        return False

    finally:
        try:
            if ssl_sock: ssl_sock.close()
            elif sock:   sock.close()
        except:
            pass
        gc.collect()


# --- MAIN EXECUTION ---
if connect_wifi():
    sync_ntp()

mqtt = None
last_publish_ms = 0

while True:
    now = time.ticks_ms()

    # 1. WiFi health check
    if not network.WLAN(network.STA_IF).isconnected():
        print("[System] WiFi lost. Reconnecting...")
        mqtt = None
        if not connect_wifi():
            time.sleep(5)
            continue

    # 2. MQTT health check / reconnect
    if mqtt is None:
        try:
            mqtt = mqtt_connect()
        except Exception as e:
            print("[Error] MQTT connect failed:", e)
            gc.collect()
            time.sleep(10)
            continue

    # 3. Read sensors and publish on interval
    if time.ticks_diff(now, last_publish_ms) >= PUBLISH_EVERY * 1000:
        measured_at = get_timestamp()

        # --- Sensor 1: SHARP distance ---
        distance, reason = read_sharp_distance_cm()
        if distance is not None:
            print("[Sensor1] distance={}cm".format(distance))
            ok = publish_to_aws(mqtt, TOPIC_DISTANCE, {
                "device_id":   DEVICE_ID,
                "sensor_type": "distance",
                "value":       distance,
                "unit":        "cm",
                "measured_at": measured_at
            })
            if not ok:
                mqtt = None
            gc.collect()  # free MQTT payload allocs before opening SSL socket
            post_to_laravel(1, distance, "cm", "distance")
            # post_to_laravel closes its socket in finally block — collect again
            gc.collect()
        else:
            print("[Sensor1] Skipped -", reason)

        # --- Sensor 2: digital switch ---
        switched = read_switch()
        print("[Sensor2] switch={}  ({})".format(
            switched, "CLOSED/active" if switched else "open"
        ))
        if mqtt is not None:
            ok = publish_to_aws(mqtt, TOPIC_SWITCH, {
                "device_id":   DEVICE_ID,
                "sensor_type": "switch",
                "value":       switched,
                "unit":        "binary",
                "measured_at": measured_at
            })
            if not ok:
                mqtt = None
            gc.collect()  # free MQTT payload allocs before opening SSL socket
        post_to_laravel(2, switched, "binary", "digital_input")
        gc.collect()

        last_publish_ms = time.ticks_ms()

    gc.collect()
    time.sleep(1)

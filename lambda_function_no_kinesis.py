import json
import os
from datetime import datetime, timezone
import urllib.request
import urllib.error

# --- CONFIG (set these as Lambda environment variables) ---
INFLUXDB_URL    = os.environ["INFLUXDB_URL"]     # e.g. https://us-east-1-1.aws.cloud2.influxdata.com
INFLUXDB_TOKEN  = os.environ["INFLUXDB_TOKEN"]
INFLUXDB_ORG    = os.environ["INFLUXDB_ORG"]
INFLUXDB_BUCKET = os.environ["INFLUXDB_BUCKET"]


def to_line_protocol(payload, arrival_time):
    """
    Convert payload to InfluxDB line protocol format.
    measurement,tag_key=tag_value field_key=field_value timestamp
    """
    device_id   = payload["device_id"]
    sensor_type = payload["sensor_type"]
    value       = float(payload["value"])
    unit        = payload.get("unit", "")

    if "measured_at" in payload:
        ts = datetime.fromisoformat(payload["measured_at"].replace("Z", "+00:00"))
    else:
        ts = arrival_time

    timestamp_ns = int(ts.timestamp() * 1_000_000_000)

    line = (
        f"sensor_readings,"
        f"device_id={device_id},"
        f"sensor_type={sensor_type},"
        f"unit={unit} "
        f"value={value} "
        f"{timestamp_ns}"
    )
    return line


def write_to_influxdb(lines):
    """Write line protocol data to InfluxDB Cloud via HTTP."""
    body = "\n".join(lines).encode("utf-8")
    url  = f"{INFLUXDB_URL}/api/v2/write?org={INFLUXDB_ORG}&bucket={INFLUXDB_BUCKET}&precision=ns"

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Token {INFLUXDB_TOKEN}",
            "Content-Type": "text/plain; charset=utf-8",
        }
    )

    with urllib.request.urlopen(req) as resp:
        print(f"[InfluxDB] Write OK, status={resp.status}, lines={len(lines)}")


def lambda_handler(event, context):
    # IoT Rule `lambda` action invokes this function with the MQTT message payload
    # as the event (a single JSON object — no Records array, no base64 encoding).
    arrival_time = datetime.now(timezone.utc)
    try:
        print(f"[Record] {event}")
        line = to_line_protocol(event, arrival_time)
        write_to_influxdb([line])
    except urllib.error.HTTPError as e:
        print(f"[Error] InfluxDB write failed: {e.code} {e.read()}")
        raise
    except Exception as e:
        print(f"[Error] Failed to process record: {e} | raw={event}")
        raise

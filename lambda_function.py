import base64
import json
import os
from datetime import datetime, timezone
#import boto3
import urllib.request
import urllib.error

# --- CONFIG (set these as Lambda environment variables) ---
INFLUXDB_URL    = os.environ["INFLUXDB_URL"]     # e.g. https://us-east-1-1.aws.cloud2.influxdata.com
INFLUXDB_TOKEN  = os.environ["INFLUXDB_TOKEN"]
INFLUXDB_ORG    = os.environ["INFLUXDB_ORG"]
INFLUXDB_BUCKET = os.environ["INFLUXDB_BUCKET"]  # esp8266-sensors

# SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
# sns = boto3.client("sns")


def parse_record(kinesis_record):
    """Decode and parse a single Kinesis record."""
    raw  = base64.b64decode(kinesis_record["data"])
    return json.loads(raw)


def to_line_protocol(payload, arrival_time):
    """
    Convert payload to InfluxDB line protocol format.
    measurement,tag_key=tag_value field_key=field_value timestamp

    device_id and sensor_type are tags (indexed, used for filtering).
    value is the field (the actual measurement).
    """
    device_id   = payload["device_id"]
    sensor_type = payload["sensor_type"]
    value       = float(payload["value"])
    unit        = payload.get("unit", "")

    # Use measured_at from payload if present, otherwise fall back to arrival time
    if "measured_at" in payload:
        ts = datetime.fromisoformat(payload["measured_at"].replace("Z", "+00:00"))
    else:
        ts = arrival_time

    timestamp_ns = int(ts.timestamp() * 1_000_000_000)  # InfluxDB expects nanoseconds

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


# def check_switch_alert(payload):
#     """Publish SNS alert if switch is active (value == 1)."""
#     if payload.get("sensor_type") == "switch" and payload.get("value") == 1:
#         device_id = payload.get("device_id", "unknown")
#         message   = f"ALERT: Switch active on {device_id} at {payload.get('measured_at', 'unknown time')}"
#         sns.publish(
#             TopicArn=SNS_TOPIC_ARN,
#             Subject=f"IoT Alert — Switch Active [{device_id}]",
#             Message=message
#         )
#         print(f"[SNS] Alert sent for {device_id}")


def lambda_handler(event, context):
    records    = event["Records"]
    lines      = []
    arrival_time = datetime.now(timezone.utc)

    for rec in records:
        try:
            payload = parse_record(rec["kinesis"])
            print(f"[Record] {payload}")

            line = to_line_protocol(payload, arrival_time)
            lines.append(line)

            # check_switch_alert(payload)

        except Exception as e:
            print(f"[Error] Failed to process record: {e} | raw={rec['kinesis']['data']}")
            # Continue processing remaining records rather than failing the whole batch

    if lines:
        try:
            write_to_influxdb(lines)
        except urllib.error.HTTPError as e:
            print(f"[Error] InfluxDB write failed: {e.code} {e.read()}")
            raise  # Re-raise so Lambda retries the batch from Kinesis

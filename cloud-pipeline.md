# IoT Cloud Pipeline — Setup Summary

## Full Pipeline

```
ESP8266 / Simulator → AWS IoT Core → Kinesis → Lambda → InfluxDB → Grafana
```

---

## Device & Code

**Hardware:** ESP8266 D1 Mini with SHARP 2Y0A21 IR distance sensor (A0) and digital switch (D2/GPIO4)

**Files:**

| File | Purpose |
|---|---|
| `boot.py` | Minimal boot, sets GC threshold, disables OS debug |
| `main.py` | WiFi connect, NTP sync, MQTT loop with WiFi/MQTT health checks |
| `config.py` | SSID, password, API credentials (gitignored) |
| `config.example.py` | Template for repo |
| `simulator.py` | PC-based device simulator publishing to same topics/payload format |

**Payload schema:**
```json
{
    "device_id": "esp8266-box1",
    "sensor_type": "distance",
    "value": 42.4,
    "unit": "cm",
    "measured_at": "2026-04-06T14:07:08Z"
}
```

**MQTT topics:**
- `esp8266/box1/distance`
- `esp8266/box1/switch`

---

## AWS IoT Core

- Created a **Thing**: `esp8266-box1`
- Auto-generated certificates — downloaded device cert, private key, public key, root CA
- Converted certs to PKCS#1 DER format for ESP8266 axTLS compatibility
- **Policy**: `esp8266-box1-policies` (version 3 active)

```json
{
    "iot:Connect": "arn:aws:iot:ap-southeast-2:[accountid]:client/esp8266-box1",
    "iot:Publish": "arn:aws:iot:ap-southeast-2:[accountid]:topic/esp8266/box1/*",
    "iot:Subscribe": "arn:aws:iot:ap-southeast-2:[accountid]:topicfilter/esp8266/box1/*",
    "iot:Receive": "arn:aws:iot:ap-southeast-2:[accountid]:topic/esp8266/box1/*"
}
```

---

## Kinesis

- **Stream**: `esp8266-box1-stream`
- Mode: Provisioned, 1 shard (~$13.25/month Sydney)
- Retention: 24 hours (default)

**IoT Core Rule**: `esp8266_box1_to_kinesis`
- SQL: `SELECT * FROM 'esp8266/box1/#'`
- Action: Kinesis → `esp8266-box1-stream`
- Partition key: `${topic()}`
- IAM role: existing IoT role with `kinesis:PutRecord`

---

## Lambda

- **Function**: `esp8266-kinesis-processor`
- Runtime: Python 3.12
- **IAM role**: `esp8266-kinesis-processor-role-13od00kd`
  - `AWSLambdaBasicExecutionRole` (auto-created)
  - `AmazonKinesisReadOnlyAccess` (manually attached)
- **Trigger**: Kinesis `esp8266-box1-stream`, batch size 10, Trim horizon
- **Environment variables**:

| Key | Value |
|---|---|
| `INFLUXDB_URL` | InfluxDB cloud cluster URL |
| `INFLUXDB_TOKEN` | InfluxDB API token |
| `INFLUXDB_ORG` | `IoTProject` |
| `INFLUXDB_BUCKET` | `esp8266-sensors` |
| `SNS_TOPIC_ARN` | Not yet configured |

**What Lambda does:**
- Decodes base64 Kinesis records
- Converts to InfluxDB line protocol (tags: `device_id`, `sensor_type`, `unit` / field: `value`)
- Uses `measured_at` from payload as timestamp
- Batch writes to InfluxDB
- SNS alert logic commented out (to be wired up)

---

## InfluxDB Cloud Serverless

- Region: US East 1 (Sydney not available)
- Org: `IoTProject`
- Bucket: `esp8266-sensors`, 30 day retention
- API token: All Access (created once, stored securely)
- Schema: measurement `sensor_readings`, tags `device_id`/`sensor_type`/`unit`, field `value`

**Query to verify data:**
```sql
SELECT * FROM "sensor_readings" WHERE time >= now() - interval '1 hour'
```

---

## Grafana Cloud

- Stack: `lbirchenprojectiot.grafana.net`
- Data source: InfluxDB plugin → InfluxDB Cloud Serverless, SQL query language, token auth
- **Dashboard**: IoT Project Dashboard
  - Panel 1: Distance time series — partitioned by `device_id` for multi-device support
  - Panel 2: Switch state timeline — value mappings (0=Open/green, 1=Active/red)
- Public dashboard enabled (Share externally) with time range and refresh interval controls exposed

**Distance panel query:**
```sql
SELECT time, value, device_id
FROM "sensor_readings"
WHERE time >= now() - interval '1 hour'
AND sensor_type = 'distance'
```

**Switch panel query:**
```sql
SELECT time, value
FROM "sensor_readings"
WHERE time >= now() - interval '1 hour'
AND sensor_type = 'switch'
```

---

## Still To Do

- SNS topic + email subscription + wire into Lambda
- Replace simulator with real board (pending WiFi radio issue or replacement board)
- Confluent Kafka path (Path 2) for blog comparison — delete Confluent cluster until ready to use

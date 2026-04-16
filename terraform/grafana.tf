provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_auth
}

resource "grafana_data_source" "influxdb" {
  type          = "influxdb"
  name          = "InfluxDB-IoT"
  url           = var.influxdb_url
  database_name = var.influxdb_bucket

  json_data_encoded = jsonencode({
    version       = "SQL"
    httpMode      = "POST"
    tlsSkipVerify = false
  })

  secure_json_data_encoded = jsonencode({
    token = var.influxdb_token
  })
}

resource "grafana_dashboard" "iot_dashboard" {
  config_json = templatefile("${path.module}/../iot_dashboard.json", {
    datasource_uid = grafana_data_source.influxdb.uid
  })
  overwrite = true
}

resource "grafana_dashboard_public" "iot_dashboard_public" {
  dashboard_uid          = grafana_dashboard.iot_dashboard.uid
  is_enabled             = true
  time_selection_enabled = true
  annotations_enabled    = false
  share                  = "public"
}

output "grafana_public_dashboard_url" {
  value = "${var.grafana_url}/public-dashboards/${grafana_dashboard_public.iot_dashboard_public.access_token}?refresh=30s&from=now-24h&to=now&timezone=browser"
}
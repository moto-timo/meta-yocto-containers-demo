#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""IoT Edge Gateway - Sensor Data Processor

Simulates temperature, humidity and pressure sensors, publishes raw
readings to MQTT, computes rolling statistics, and publishes the
processed results back.  Designed to run inside an OCI container
alongside a Mosquitto broker.

Topics:
    sensors/raw/<sensor_id>         - individual readings  (JSON)
    sensors/processed/<sensor_id>   - rolling statistics   (JSON)
    sensors/status                  - service heartbeat    (JSON)
"""

import json
import math
import os
import random
import signal
import sys
import time
from collections import deque

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Configuration (overridable via environment)
# ---------------------------------------------------------------------------
MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
CLIENT_ID = os.environ.get("CLIENT_ID", "sensor-processor")
PUBLISH_INTERVAL = float(os.environ.get("PUBLISH_INTERVAL", "2.0"))
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", "10"))

# ---------------------------------------------------------------------------
# Simulated sensors
# ---------------------------------------------------------------------------
SENSORS = {
    "temp-01": {
        "type": "temperature",
        "unit": "\u00b0C",
        "base": 22.0,
        "variance": 3.0,
    },
    "humid-01": {
        "type": "humidity",
        "unit": "%",
        "base": 55.0,
        "variance": 10.0,
    },
    "press-01": {
        "type": "pressure",
        "unit": "hPa",
        "base": 1013.25,
        "variance": 5.0,
    },
}

# Rolling windows keyed by sensor id
windows = {sid: deque(maxlen=WINDOW_SIZE) for sid in SENSORS}

running = True


def _shutdown(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def simulate_reading(sensor_id, tick):
    """Return a realistic sensor value with slow drift and noise."""
    cfg = SENSORS[sensor_id]
    drift = math.sin(tick * 0.1) * cfg["variance"] * 0.5
    noise = random.gauss(0, cfg["variance"] * 0.2)
    return round(cfg["base"] + drift + noise, 2)


def compute_stats(values):
    """Compute mean / min / max over a sliding window."""
    n = len(values)
    if n == 0:
        return {"mean": 0, "min": 0, "max": 0, "count": 0}
    mean = sum(values) / n
    return {
        "mean": round(mean, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "count": n,
    }


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------
def on_connect(client, _userdata, _flags, reason_code, _properties=None):
    print(f"[sensor-processor] connected to {MQTT_HOST}:{MQTT_PORT} "
          f"(rc={reason_code})", flush=True)
    client.subscribe("sensors/raw/#")


def on_message(_client, _userdata, msg):
    """Ingest raw readings published by *this* service (or external sources)."""
    try:
        data = json.loads(msg.payload)
        sensor_id = msg.topic.rsplit("/", 1)[-1]
        if sensor_id in windows:
            windows[sensor_id].append(data["value"])
    except (json.JSONDecodeError, KeyError):
        pass


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    print(f"[sensor-processor] starting  host={MQTT_HOST} port={MQTT_PORT} "
          f"interval={PUBLISH_INTERVAL}s window={WINDOW_SIZE}", flush=True)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        clean_session=True,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    # Set with mqtt-auth
    if os.environ.get("MQTT_USERNAME"):
        client.username_pw_set(os.environ["MQTT_USERNAME"], os.environ.get("MQTT_PASSWORD"))

    # Retry until the broker is reachable
    while running:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except OSError:
            print("[sensor-processor] broker not ready, retrying in 2 s ...",
                  flush=True)
            time.sleep(2)

    client.loop_start()

    tick = 0
    try:
        while running:
            ts = time.time()

            for sensor_id, cfg in SENSORS.items():
                value = simulate_reading(sensor_id, tick)

                # Publish raw reading
                client.publish(
                    f"sensors/raw/{sensor_id}",
                    json.dumps({
                        "sensor_id": sensor_id,
                        "type": cfg["type"],
                        "value": value,
                        "unit": cfg["unit"],
                        "timestamp": ts,
                    }),
                    qos=0,
                )

                # Publish rolling statistics
                stats = compute_stats(list(windows[sensor_id]))
                client.publish(
                    f"sensors/processed/{sensor_id}",
                    json.dumps({
                        "sensor_id": sensor_id,
                        "type": cfg["type"],
                        "unit": cfg["unit"],
                        "stats": stats,
                        "window_size": WINDOW_SIZE,
                        "timestamp": ts,
                    }),
                    qos=0,
                )

            # Heartbeat
            client.publish(
                "sensors/status",
                json.dumps({
                    "service": CLIENT_ID,
                    "uptime_ticks": tick,
                    "sensors": list(SENSORS.keys()),
                    "timestamp": ts,
                }),
                qos=0,
            )

            tick += 1
            time.sleep(PUBLISH_INTERVAL)

    finally:
        print("[sensor-processor] shutting down", flush=True)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

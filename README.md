# Tuya MQTT Bridge

A lightweight, containerized bridge that connects **Tuya smart devices** (via local LAN using TinyTuya) to a **Mosquitto MQTT broker** — with automatic **Home Assistant MQTT Discovery** and a clean **NiceGUI web interface** for device management.

---

## Features

- **Local-first control** — communicates directly with Tuya devices on your LAN (no cloud dependency)
- **MQTT publishing** — pushes device state and availability to your existing Mosquitto broker
- **Home Assistant Discovery** — entities auto-appear in HA on first successful device poll
- **NiceGUI dashboard** — add, edit, delete, and monitor devices via a web UI
- **SQLite persistence** — device config survives container restarts
- **Hot reload** — add or remove devices at runtime without restarting the container
- **Docker-ready** — single `docker compose up` to get started

---

## Screenshots

> Dashboard showing live device status, DPS values, and online/offline state.

```text
┌─────────────────────────────────────────────────────────────┐
│  Tuya MQTT Bridge                                 [+] Add   │
├─────────────────────────────────────────────────────────────┤
│  Total: 4   Online: 3   Offline: 1   Disabled: 0            │
├──────────────────┬──────────────────┬───────────────────────┤
│ Living Room Plug │ Bedroom Switch   │ Kitchen Sensor        │
│ ● Online         │ ● Online         │ ✗ Offline             │
│ IP: 192.168.1.10 │ IP: 192.168.1.11 │ IP: 192.168.1.12      │
│ DPS: 1:true      │ DPS: 1:false     │ Last seen: 14:32:01   │
└──────────────────┴──────────────────┴───────────────────────┘
```

---

## Architecture

```text
Tuya Device (LAN)
      │
      │  TinyTuya (local key, direct IP)
      ▼
┌─────────────────┐
│  tuya/poller.py │  ← async thread pool, polls every N seconds
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│  bridge/manager.py   │  ← orchestrates pollers, normalizes state
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  mqtt/publisher.py   │  ← publishes state, availability, HA discovery
└────────┬─────────────┘
         │
         ▼
  Mosquitto MQTT Broker
         │
         ▼
  Home Assistant  (entities auto-created via MQTT Discovery)
```

**UI layer** (NiceGUI) runs alongside the bridge in the same process, reading/writing SQLite and calling bridge manager directly.

---

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Docker + Docker Compose | v2.x recommended |
| Mosquitto MQTT broker | Already running in a container |
| Tuya device credentials | `DEVICEID`, `DEVICEIP`, `DEVICEKEY`, protocol version |
| LAN access to devices | Container must be on same network as Tuya devices |

> **Getting Tuya credentials?** Use the [TinyTuya Setup Wizard](https://github.com/jasonacox/tinytuya#setup-wizard---getting-local-keys) or run: `python -m tinytuya wizard`

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/youruser/tuya-mqtt-bridge.git
cd tuya-mqtt-bridge

cp .env.example .env
```

Edit `.env`:

```env
MQTT_HOST=192.168.1.10       # Your Mosquitto broker IP
MQTT_PORT=1883
MQTT_USERNAME=your_user      # Leave blank if no auth
MQTT_PASSWORD=your_pass

POLL_INTERVAL=10             # Seconds between device polls
```

### 2. Start the container

```bash
mkdir -p data
docker compose up --build -d
```

### 3. Open the UI

```text
http://localhost:8080
```

### 4. Add your first device

Click **[+ Add]** in the top-right corner and fill in:

| Field | Example |
| --- | --- |
| Device ID | `abcdef1234567890abcd` |
| Friendly Name | `Living Room Plug` |
| Device IP | `192.168.1.100` |
| Local Key | `abcdef1234567890` |
| Version | `3.3` |

Hit **Add Device** — polling starts immediately and the device appears in Home Assistant within seconds.

---

## Project Structure

```text
tuya-mqtt-bridge/
├── app/
│   ├── main.py              # Entrypoint — NiceGUI routes + lifecycle
│   ├── config.py            # All settings from env vars
│   │
│   ├── db/
│   │   ├── database.py      # SQLite engine, CRUD helpers
│   │   └── models.py        # Device ORM model (SQLAlchemy)
│   │
│   ├── tuya/
│   │   └── poller.py        # Async TinyTuya poller (thread pool)
│   │
│   ├── mqtt/
│   │   ├── client.py        # aiomqtt singleton
│   │   ├── publisher.py     # State + availability publishing
│   │   └── discovery.py     # Home Assistant Discovery payloads
│   │
│   ├── bridge/
│   │   └── manager.py       # Orchestrator — owns all pollers
│   │
│   └── ui/
│       ├── pages/
│       │   ├── dashboard.py     # Live status cards
│       │   ├── add_device.py    # Add device form
│       │   └── edit_device.py   # Edit / delete device
│       └── components/
│           ├── device_card.py   # Reusable device status card
│           └── navbar.py        # Navigation bar
│
├── data/                    # SQLite DB volume mount
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## MQTT Topics

All topics are prefixed with `MQTT_BASE_TOPIC` (default: `tuya2mqtt`).

| Topic | Direction | Payload | Description |
| --- | --- | --- | --- |
| `tuya2mqtt/{device_id}/state` | Bridge → HA | `{"1": true, "2": 0}` | Full DPS state (JSON) |
| `tuya2mqtt/{device_id}/availability` | Bridge → HA | `online` / `offline` | Device reachability |
| `tuya2mqtt/{device_id}/set/{dps}` | HA → Bridge | `{"dps": "1", "value": true}` | Command to set a DPS value |

### Example state message

```json
// tuya2mqtt/abcdef1234567890abcd/state
{
  "1": true,
  "9": 2600,
  "18": 117,
  "19": 128,
  "20": 2351
}
```

---

## Home Assistant Integration

MQTT Discovery is **enabled by default** (`HA_DISCOVERY_ENABLED=true`).

On first successful poll, the bridge publishes discovery configs to:

```text
homeassistant/{component}/{device_id}_{dps}/config
```

### Auto-created entity types

| DPS Value Type | HA Entity | Example |
| --- | --- | --- |
| `bool` at key `"1"` | `switch` | Main on/off switch |
| `bool` at other keys | `binary_sensor` | Status flags |
| `int` / `float` | `sensor` | Power, voltage, current |

> Entities appear under **Settings → Devices & Services → MQTT** in Home Assistant.

### Manual HA YAML (optional override)

```yaml
# configuration.yaml
mqtt:
  sensor:
    - name: "Living Room Plug Power"
      state_topic: "tuya2mqtt/abcdef1234567890abcd/state"
      value_template: "{{ value_json['19'] | float / 10 }}"
      unit_of_measurement: "W"
      availability_topic: "tuya2mqtt/abcdef1234567890abcd/availability"
```

---

## Configuration Reference

All settings via environment variables (`.env` file):

```env
# ── MQTT ────────────────────────────────────────────
MQTT_HOST=localhost            # Broker hostname or IP
MQTT_PORT=1883                 # Default MQTT port
MQTT_USERNAME=                 # Leave blank for no auth
MQTT_PASSWORD=
MQTT_BASE_TOPIC=tuya2mqtt      # Root topic prefix

# ── Home Assistant Discovery ─────────────────────────
HA_DISCOVERY_ENABLED=true
HA_DISCOVERY_PREFIX=homeassistant

# ── Bridge ───────────────────────────────────────────
POLL_INTERVAL=10               # Seconds between polls
DEVICE_TIMEOUT=6               # TinyTuya connect timeout (seconds)

# ── UI ───────────────────────────────────────────────
UI_HOST=0.0.0.0
UI_PORT=8080
UI_TITLE=Tuya MQTT Bridge

# ── Storage ──────────────────────────────────────────
DB_PATH=/data/devices.db       # SQLite path (use volume mount)

# ── Logging ──────────────────────────────────────────
LOG_LEVEL=INFO                 # DEBUG | INFO | WARNING | ERROR
```

---

## Docker Details

### Why `network_mode: host`?

TinyTuya communicates with devices using their **direct LAN IP addresses** on UDP/TCP. Docker bridge networking blocks this. `host` mode is the most reliable option for LAN IoT projects.

### Volume mounts

| Host path | Container path | Purpose |
| --- | --- | --- |
| `./data` | `/data` | SQLite database persistence |
| `./.env` | `/app/.env` | Configuration |

### Build and run

```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f tuya-mqtt-bridge

# Restart
docker compose restart tuya-mqtt-bridge

# Stop
docker compose down
```

---

## Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp .env.example .env

# Create data dir and run
mkdir -p data
python -m app.main
```

---

## Troubleshooting

### `no such table: devices` on first run

```text
[ERROR] nicegui: (sqlite3.OperationalError) no such table: devices
[SQL: SELECT devices.device_id AS devices_device_id, ... FROM devices]
```

**Cause, reproduced in a container.** `data/devices.db` exists but is not writable by the
user inside the image, which runs as uid 1000. Schema creation fails with `attempt to
write a readonly database`, the app logs that once at startup and keeps serving, and every
page render afterwards runs a SELECT that opens the file successfully and reports the
missing table. So the message you keep seeing names the table, while the real cause is a
file permission and it has already scrolled past.

The usual way to get there: `docker compose up` creates a missing `./data` owned by root,
because `data/` is gitignored and so absent from a fresh clone.

**Fixed in the app.** The schema is now created when the database module is imported, and a
failure raises immediately naming the path and the user id, so the container stops with the
real cause instead of serving errors that blame the schema.

**Workaround on an older build:**

```bash
mkdir -p data && sudo chown -R 1000:1000 data
docker compose down && docker compose up -d
```

Note for completeness: with a writable `data/` the older build does start and serve, even
with no broker reachable. A failed MQTT connect used to abort the rest of startup so the
device pollers never began, which is fixed too, but it is not what produced this error.

### Device shows as Offline

```bash
# 1. Verify device is reachable from the host
ping 192.168.1.100

# 2. Test TinyTuya directly
python -c "
import tinytuya
d = tinytuya.OutletDevice('DEVICEID', '192.168.1.100', 'LOCALKEY', version=3.3)
print(d.status())
"

# 3. Check logs for errors
docker compose logs -f tuya-mqtt-bridge | grep ERROR
```

### MQTT not connecting

```bash
# Test broker connection from host
mosquitto_pub -h 192.168.1.10 -t test/ping -m hello
mosquitto_sub -h 192.168.1.10 -t test/ping

# Check MQTT credentials in .env
# Verify broker allows connections from the bridge container
```

### Entities not appearing in Home Assistant

```bash
# Check discovery topics are being published
mosquitto_sub -h 192.168.1.10 -t 'homeassistant/#' -v

# Verify HA MQTT integration is set up:
# Settings → Devices & Services → Add Integration → MQTT
```

### Wrong device version

Most Tuya devices use `3.3`. If getting errors try:
- `3.4` for newer Smart Life / Tuya app devices
- `3.5` for very recent devices
- `3.1` for legacy devices (pre-2019)

---

## Roadmap

- [ ] MQTT command handler (HA → device control via `set/{dps}`)
- [ ] Device scan page (auto-discover Tuya devices on LAN)
- [ ] DPS label mapping (name DPS keys per device type)
- [ ] Multi-DPS templates (map raw values to human-readable units)
- [ ] Webhook / REST API endpoint for external triggers
- [ ] Prometheus metrics endpoint

---

## Dependencies

| Package | Purpose |
| --- | --- |
| [tinytuya](https://github.com/jasonacox/tinytuya) | Local Tuya device communication |
| [aiomqtt](https://github.com/empicano/aiomqtt) | Async MQTT client |
| [nicegui](https://nicegui.io) | Web UI framework |
| [SQLAlchemy](https://www.sqlalchemy.org) | ORM + SQLite |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `.env` file loading |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [TinyTuya](https://github.com/jasonacox/tinytuya) by Jason Cox — the backbone of local Tuya control
- [NiceGUI](https://nicegui.io) — Python-native UI that makes web dashboards painless
- [Home Assistant](https://www.home-assistant.io) — the smart home hub this project is built around

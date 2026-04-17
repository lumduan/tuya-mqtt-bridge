"""
app/mqtt/publisher.py
Publishes device state to MQTT and registers HA Discovery configs.
"""
import json
import logging

from app.config import config
from app.mqtt.client import mqtt_client

logger = logging.getLogger(__name__)

BASE = config.mqtt.base_topic
HA_PREFIX = config.mqtt.ha_discovery_prefix


def _state_topic(device_id: str) -> str:
    return f"{BASE}/{device_id}/state"


def _availability_topic(device_id: str) -> str:
    return f"{BASE}/{device_id}/availability"


def _command_topic(device_id: str, dps_key: str) -> str:
    return f"{BASE}/{device_id}/set/{dps_key}"


async def publish_state(device_id: str, dps: dict):
    """Publish full DPS state as JSON."""
    topic = _state_topic(device_id)
    payload = json.dumps(dps)
    await mqtt_client.publish(topic, payload, retain=True)


async def publish_availability(device_id: str, online: bool):
    """Publish device online/offline status."""
    topic = _availability_topic(device_id)
    await mqtt_client.publish(topic, "online" if online else "offline", retain=True)


async def publish_ha_discovery(device_id: str, device_name: str, dps: dict):
    """
    Auto-register entities in Home Assistant via MQTT Discovery.

    Strategy:
      - DPS "1" (bool)  → switch entity
      - DPS numeric     → sensor entity
      - Other bool DPS  → binary_sensor entity
    """
    if not config.mqtt.ha_discovery_enabled:
        return

    device_info = {
        "identifiers": [device_id],
        "name": device_name,
        "manufacturer": "Tuya",
        "model": "Generic Tuya Device",
        "via_device": "tuya_mqtt_bridge",
    }

    for dps_key, value in dps.items():
        entity_id = f"{device_id}_{dps_key}"
        avail_topic = _availability_topic(device_id)
        state_topic = _state_topic(device_id)

        if dps_key == "1" and isinstance(value, bool):
            # Main switch
            component = "switch"
            config_payload = {
                "name": f"{device_name} Switch",
                "unique_id": f"tuya_{entity_id}",
                "state_topic": state_topic,
                "command_topic": _command_topic(device_id, dps_key),
                "value_template": "{{ 'ON' if value_json['1'] else 'OFF' }}",
                "payload_on": json.dumps({"dps": dps_key, "value": True}),
                "payload_off": json.dumps({"dps": dps_key, "value": False}),
                "availability_topic": avail_topic,
                "device": device_info,
            }
        elif isinstance(value, bool):
            # Other boolean DPS → binary sensor
            component = "binary_sensor"
            config_payload = {
                "name": f"{device_name} DPS {dps_key}",
                "unique_id": f"tuya_{entity_id}",
                "state_topic": state_topic,
                "value_template": f"{{% raw %}}{{{{ 'ON' if value_json['{dps_key}'] else 'OFF' }}}}{{% endraw %}}",
                "availability_topic": avail_topic,
                "device": device_info,
            }
        elif isinstance(value, (int, float)):
            # Numeric → sensor
            component = "sensor"
            config_payload = {
                "name": f"{device_name} DPS {dps_key}",
                "unique_id": f"tuya_{entity_id}",
                "state_topic": state_topic,
                "value_template": f"{{% raw %}}{{{{ value_json['{dps_key}'] }}}}{{% endraw %}}",
                "availability_topic": avail_topic,
                "device": device_info,
            }
        else:
            continue  # Skip string/unknown DPS

        discovery_topic = f"{HA_PREFIX}/{component}/{entity_id}/config"
        await mqtt_client.publish(
            discovery_topic,
            json.dumps(config_payload),
            retain=True,
        )
        logger.debug("HA Discovery → %s", discovery_topic)

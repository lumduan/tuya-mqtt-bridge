"""
app/bridge/manager.py
Central bridge manager — owns device pollers, handles state updates,
and publishes to MQTT. Hot-reloadable: devices can be added/removed at runtime.
"""
import asyncio
import json
import logging
from typing import Dict

from app.db.database import get_all_devices, update_device_status
from app.mqtt.client import mqtt_client
from app.mqtt.publisher import publish_state, publish_availability, publish_ha_discovery
from app.tuya.poller import DevicePoller

logger = logging.getLogger(__name__)


class BridgeManager:
    def __init__(self):
        self._pollers: Dict[str, DevicePoller] = {}
        self._device_names: Dict[str, str] = {}
        self._ha_discovered: set[str] = set()  # track devices already announced

    async def start(self):
        """Connect MQTT and start pollers for all enabled DB devices."""
        await mqtt_client.connect()
        devices = get_all_devices()
        for device in devices:
            if device.enabled:
                await self.add_device_poller(device)
        logger.info("Bridge started with %d device(s)", len(self._pollers))

    async def stop(self):
        """Gracefully stop all pollers and disconnect MQTT."""
        for poller in self._pollers.values():
            await poller.stop()
        self._pollers.clear()
        await mqtt_client.disconnect()
        logger.info("Bridge stopped")

    async def add_device_poller(self, device):
        """Start polling a device. Safe to call at runtime."""
        device_id = device.device_id
        if device_id in self._pollers:
            logger.debug("Poller already running for %s", device_id)
            return

        self._device_names[device_id] = device.name

        poller = DevicePoller(
            device_id=device_id,
            ip=device.ip,
            key=device.key,
            version=device.version,
            persist=device.persist,
            name=device.name,
            on_update=self._handle_update,
        )
        poller.start()
        self._pollers[device_id] = poller
        logger.info("Started poller for %s (%s)", device.name, device_id)

    async def remove_device_poller(self, device_id: str):
        """Stop and remove a device poller."""
        poller = self._pollers.pop(device_id, None)
        if poller:
            await poller.stop()
            await publish_availability(device_id, online=False)
            logger.info("Removed poller for %s", device_id)

    async def reload_device(self, device_id: str, device=None):
        """Restart poller for a device (after edit)."""
        await self.remove_device_poller(device_id)
        if device and device.enabled:
            await self.add_device_poller(device)

    async def _handle_update(self, device_id: str, dps: dict, is_online: bool):
        """Callback from DevicePoller — publish to MQTT, update DB."""
        device_name = self._device_names.get(device_id, device_id)

        # Update DB status
        update_device_status(
            device_id,
            is_online=is_online,
            status_json=json.dumps(dps) if dps else None,
        )

        # Publish availability
        await publish_availability(device_id, is_online)

        if not is_online or not dps:
            return

        # Publish state
        await publish_state(device_id, dps)

        # Send HA Discovery on first successful poll
        if device_id not in self._ha_discovered:
            await publish_ha_discovery(device_id, device_name, dps)
            self._ha_discovered.add(device_id)

    def get_status(self) -> dict:
        """Return runtime status summary for the UI."""
        return {
            device_id: {
                "name": self._device_names.get(device_id, device_id),
                "running": not poller._task.done() if poller._task else False,
            }
            for device_id, poller in self._pollers.items()
        }


# Singleton
bridge_manager = BridgeManager()

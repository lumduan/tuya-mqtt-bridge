"""
app/tuya/poller.py
Async device poller — runs TinyTuya (blocking) in a thread pool,
emits state updates via asyncio.Queue.
"""
import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable

import tinytuya

from app.config import config

logger = logging.getLogger(__name__)


class DevicePoller:
    """
    Wraps a single TinyTuya device and polls it at a fixed interval.
    On each successful poll, calls the `on_update` callback with:
        (device_id: str, dps: dict, is_online: bool)
    """

    def __init__(
        self,
        device_id: str,
        ip: str,
        key: str,
        version: float,
        persist: bool,
        name: str,
        on_update: Callable[[str, dict, bool], Awaitable[None]],
    ):
        self.device_id = device_id
        self.ip = ip
        self.key = key
        self.version = version
        self.persist = persist
        self.name = name
        self.on_update = on_update

        self._task: Optional[asyncio.Task] = None
        self._running = False

    def _create_device(self) -> tinytuya.OutletDevice:
        d = tinytuya.OutletDevice(
            dev_id=self.device_id,
            address=self.ip,
            local_key=self.key,
            version=self.version,
            persist=self.persist,
        )
        d.set_socketTimeout(config.bridge.device_timeout)
        return d

    def _blocking_poll(self) -> Optional[dict]:
        """Runs in thread pool — do NOT await here."""
        try:
            device = self._create_device()
            data = device.status()
            if "dps" in data:
                return data["dps"]
            if "Error" in data:
                logger.warning("[%s] Poll error: %s", self.name, data.get("Error"))
            return None
        except Exception as exc:
            logger.debug("[%s] Poll exception: %s", self.name, exc)
            return None

    async def _poll_loop(self):
        loop = asyncio.get_running_loop()
        self._running = True
        logger.info("[%s] Poller started (every %ds)", self.name, config.bridge.poll_interval)

        while self._running:
            dps = await loop.run_in_executor(None, self._blocking_poll)
            is_online = dps is not None

            try:
                await self.on_update(self.device_id, dps or {}, is_online)
            except Exception as exc:
                logger.error("[%s] on_update callback error: %s", self.name, exc)

            await asyncio.sleep(config.bridge.poll_interval)

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[%s] Poller stopped", self.name)

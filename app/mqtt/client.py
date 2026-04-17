"""
app/mqtt/client.py
Async MQTT client singleton using aiomqtt.
"""
import asyncio
import logging
from typing import Optional
import aiomqtt

from app.config import config

logger = logging.getLogger(__name__)


class MQTTClient:
    """
    Manages a persistent async MQTT connection.
    Provides publish() for use throughout the app.
    """

    def __init__(self):
        self._client: Optional[aiomqtt.Client] = None
        self._lock = asyncio.Lock()
        self._connected = False

    async def connect(self):
        cfg = config.mqtt
        kwargs = dict(hostname=cfg.host, port=cfg.port)
        if cfg.username:
            kwargs["username"] = cfg.username
            kwargs["password"] = cfg.password

        self._client = aiomqtt.Client(**kwargs)
        await self._client.__aenter__()
        self._connected = True
        logger.info("MQTT connected to %s:%d", cfg.host, cfg.port)

    async def disconnect(self):
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._connected = False
            logger.info("MQTT disconnected")

    async def publish(self, topic: str, payload: str, retain: bool = False, qos: int = 0):
        if not self._connected or not self._client:
            logger.warning("MQTT not connected, skipping publish to %s", topic)
            return
        async with self._lock:
            await self._client.publish(topic, payload=payload, qos=qos, retain=retain)
            logger.debug("MQTT → %s : %s", topic, payload)

    @property
    def is_connected(self) -> bool:
        return self._connected


# Singleton
mqtt_client = MQTTClient()

"""
app/config.py
Centralized configuration loaded from environment variables.
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MQTTConfig:
    host: str = field(default_factory=lambda: os.getenv("MQTT_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MQTT_PORT", "1883")))
    username: str = field(default_factory=lambda: os.getenv("MQTT_USERNAME", ""))
    password: str = field(default_factory=lambda: os.getenv("MQTT_PASSWORD", ""))
    base_topic: str = field(default_factory=lambda: os.getenv("MQTT_BASE_TOPIC", "tuya2mqtt"))
    ha_discovery_enabled: bool = field(
        default_factory=lambda: os.getenv("HA_DISCOVERY_ENABLED", "true").lower() == "true"
    )
    ha_discovery_prefix: str = field(
        default_factory=lambda: os.getenv("HA_DISCOVERY_PREFIX", "homeassistant")
    )


@dataclass
class BridgeConfig:
    poll_interval: int = field(default_factory=lambda: int(os.getenv("POLL_INTERVAL", "10")))
    device_timeout: int = field(default_factory=lambda: int(os.getenv("DEVICE_TIMEOUT", "6")))


@dataclass
class UIConfig:
    host: str = field(default_factory=lambda: os.getenv("UI_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("UI_PORT", "8080")))
    title: str = field(default_factory=lambda: os.getenv("UI_TITLE", "Tuya MQTT Bridge"))


@dataclass
class AppConfig:
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "/data/devices.db"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    ui: UIConfig = field(default_factory=UIConfig)


# Singleton instance
config = AppConfig()

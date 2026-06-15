"""Shared configuration for the AGV integration harness."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HarnessConfig:
    """Runtime configuration for MQTT topics and timeouts."""

    manufacturer: str = os.environ.get("AGV_MANUFACTURER", "DATN")
    version: str = os.environ.get("AGV_VERSION", "2.1.0")
    serial_number: str = os.environ.get("AGV_SERIAL", "CDEF")
    mqtt_broker: str = os.environ.get("MQTT_BROKER", "127.0.0.1")
    mqtt_port: int = int(os.environ.get("MQTT_PORT", "1884"))
    keepalive_s: int = int(os.environ.get("MQTT_KEEPALIVE", "60"))
    default_timeout_s: float = float(os.environ.get("HARNESS_TIMEOUT", "20"))
    heartbeat_wait_s: float = float(os.environ.get("HEARTBEAT_WAIT", "35"))

    @property
    def base_topic(self) -> str:
        return f"uagv/v2/{self.manufacturer}/{self.serial_number}"

    @property
    def connection_topic(self) -> str:
        return f"{self.base_topic}/connection"

    @property
    def state_topic(self) -> str:
        return f"{self.base_topic}/state"

    @property
    def order_topic(self) -> str:
        return f"{self.base_topic}/order"

    @property
    def instant_actions_topic(self) -> str:
        return f"{self.base_topic}/instantActions"


def get_config() -> HarnessConfig:
    """Return the active harness configuration."""

    return HarnessConfig()

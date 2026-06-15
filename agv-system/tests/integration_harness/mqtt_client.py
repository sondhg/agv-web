"""MQTT helper for publishing and observing AGV messages."""

from __future__ import annotations

import json
import queue
import time
import threading
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt

from .config import HarnessConfig


@dataclass(frozen=True)
class MqttMessage:
    """Captured MQTT message with parsed JSON payload when available."""

    topic: str
    payload: dict[str, Any]
    raw_payload: bytes


class HarnessMqttClient:
    """Small MQTT wrapper with topic subscription and message waiting."""

    def __init__(self, config: HarnessConfig):
        self._config = config
        self._client = mqtt.Client(client_id=f"integration_harness_{config.serial_number}")
        self._messages: queue.Queue[MqttMessage] = queue.Queue()
        self._connected = threading.Event()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected.set()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except ValueError:
            payload = {}
        self._messages.put(MqttMessage(topic=msg.topic, payload=payload, raw_payload=msg.payload))

    def connect(self) -> None:
        """Connect to the broker and start background network processing."""

        self._client.connect(self._config.mqtt_broker, self._config.mqtt_port, self._config.keepalive_s)
        self._client.loop_start()
        if not self._connected.wait(timeout=5):
            self.close()
            raise TimeoutError(
                f"Unable to connect to MQTT broker {self._config.mqtt_broker}:{self._config.mqtt_port}"
            )

    def close(self) -> None:
        """Stop network processing and close the MQTT connection."""

        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            self._connected.clear()

    def subscribe(self, topics: list[str]) -> None:
        """Subscribe to one or more topics."""

        for topic in topics:
            self._client.subscribe(topic, qos=1)

    def publish_json(self, topic: str, payload: dict[str, Any], qos: int = 1, retain: bool = False) -> None:
        """Publish a JSON payload."""

        self._client.publish(topic, json.dumps(payload), qos=qos, retain=retain)

    def wait_for(self, topic: str, *, predicate=None, timeout_s: float = 10.0) -> MqttMessage | None:
        """Wait for a matching message on a topic."""

        deadline = time.time() + timeout_s
        buffer: list[MqttMessage] = []

        while time.time() < deadline:
            remaining = max(0.1, deadline - time.time())
            try:
                message = self._messages.get(timeout=remaining)
            except queue.Empty:
                break

            if message.topic == topic and (predicate is None or predicate(message.payload)):
                for buffered in buffer:
                    self._messages.put(buffered)
                return message

            buffer.append(message)

        for buffered in buffer:
            self._messages.put(buffered)
        return None

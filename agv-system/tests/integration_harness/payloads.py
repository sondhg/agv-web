"""Payload builders for the AGV integration tests."""

from __future__ import annotations

from datetime import datetime, timezone

from .config import HarnessConfig


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_connection_payload(config: HarnessConfig, status: str = "ONLINE") -> dict:
    """Build a VDA5050 connection payload."""

    return {
        "headerId": 0,
        "timestamp": _timestamp(),
        "version": config.version,
        "manufacturer": config.manufacturer,
        "serialNumber": config.serial_number,
        "connectionState": status,
    }


def build_state_payload(config: HarnessConfig, connection_state: str = "ONLINE") -> dict:
    """Build a minimal state payload for manual publishing or verification."""

    return {
        "headerId": 1,
        "timestamp": _timestamp(),
        "version": config.version,
        "manufacturer": config.manufacturer,
        "serialNumber": config.serial_number,
        "orderId": "",
        "lastNodeId": "",
        "lastNodeSequenceId": 0,
        "driving": False,
        "paused": False,
        "operatingMode": "AUTOMATIC",
        "batteryState": {
            "batteryCharge": 100,
            "batteryVoltage": 48.0,
            "charging": False,
            "reach": 100,
        },
        "agvPosition": {
            "x": 0.0,
            "y": 0.0,
            "theta": 0.0,
            "mapId": "map_1",
            "positionInitialized": True,
        },
        "velocity": {"vx": 0.0, "vy": 0.0, "omega": 0.0},
        "loads": [],
        "safetyState": {"eStop": "NONE", "fieldViolation": False},
        "errors": [],
        "information": [{"connectionState": connection_state}],
    }


def build_order_payload(
    config: HarnessConfig,
    *,
    order_id: str = "integration_order_1",
    order_update_id: int = 1,
) -> dict:
    """Build a compact order that matches the server's publish schema."""

    nodes = [
        {"nodeId": "node_start", "sequenceId": 0, "nodePosition": {"x": 0.0, "y": 0.0, "mapId": "map_1"}, "released": True, "actions": []},
        {"nodeId": "node_mid", "sequenceId": 2, "nodePosition": {"x": 1.0, "y": 0.0, "mapId": "map_1"}, "released": True, "actions": []},
        {"nodeId": "node_end", "sequenceId": 4, "nodePosition": {"x": 2.0, "y": 0.0, "mapId": "map_1"}, "released": True, "actions": []},
    ]

    edges = [
        {"edgeId": "edge_1", "sequenceId": 1, "startNodeId": "node_start", "endNodeId": "node_mid", "released": True},
        {"edgeId": "edge_2", "sequenceId": 3, "startNodeId": "node_mid", "endNodeId": "node_end", "released": True},
    ]

    return {
        "headerId": 2,
        "timestamp": _timestamp(),
        "version": config.version,
        "manufacturer": config.manufacturer,
        "serialNumber": config.serial_number,
        "orderId": order_id,
        "orderUpdateId": order_update_id,
        "zoneSetId": "",
        "nodes": nodes,
        "edges": edges,
    }


def build_oversized_order_payload(config: HarnessConfig, target_size_bytes: int = 2300) -> dict:
    """Build an intentionally oversized order payload for buffer testing."""

    payload = build_order_payload(config, order_id="oversized_order")
    payload["nodes"][0]["actions"] = [
        {
            "actionType": "noop",
            "actionId": "noop-1",
            "blockingType": "HARD",
            "actionParameters": [
                {"key": "pad", "value": "x" * 64}
                for _ in range(20)
            ],
        }
    ]
    payload["information"] = ["x" * 128 for _ in range(max(1, target_size_bytes // 128))]
    return payload

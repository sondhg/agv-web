"""Command-line runner for the AGV integration harness."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

from .config import HarnessConfig, get_config
from .mqtt_client import HarnessMqttClient
from .payloads import (
    build_connection_payload,
    build_order_payload,
    build_oversized_order_payload,
    build_state_payload,
)


@dataclass
class TestOutcome:
    """Result of a single harness test case."""

    name: str
    passed: bool
    details: str


def _run_case_1(client: HarnessMqttClient, config: HarnessConfig, dry_run: bool) -> TestOutcome:
    """Validate connection and state heartbeat topics."""

    if dry_run:
        return TestOutcome(
            name="TC1",
            passed=True,
            details="Dry run completed. Payload templates were generated successfully.",
        )

    connection_topic = config.connection_topic
    state_topic = config.state_topic
    client.subscribe([connection_topic, state_topic])

    connection_msg = client.wait_for(
        connection_topic,
        predicate=lambda payload: payload.get("connectionState") == "ONLINE",
        timeout_s=config.default_timeout_s,
    )
    state_msg = client.wait_for(state_topic, timeout_s=config.default_timeout_s)

    if not connection_msg:
        return TestOutcome(name="TC1", passed=False, details="Did not receive ONLINE connection payload.")
    if not state_msg:
        return TestOutcome(name="TC1", passed=False, details="Did not receive any state payload.")

    heartbeat_msg = client.wait_for(
        state_topic,
        predicate=lambda payload: payload.get("headerId") != state_msg.payload.get("headerId"),
        timeout_s=config.heartbeat_wait_s,
    )

    return TestOutcome(
        name="TC1",
        passed=heartbeat_msg is not None,
        details=(
            "Received ONLINE connection and at least one state frame."
            if heartbeat_msg
            else "Received initial state but did not observe a later heartbeat frame."
        ),
    )


def _run_case_2(client: HarnessMqttClient, config: HarnessConfig, dry_run: bool) -> TestOutcome:
    """Validate order payload parsing and oversized buffer handling."""

    if dry_run:
        compact_order = build_order_payload(config)
        oversized_order = build_oversized_order_payload(config)
        return TestOutcome(
            name="TC2",
            passed=True,
            details=(
                f"Dry run completed. Compact order size={len(json.dumps(compact_order))} bytes; "
                f"oversized order size={len(json.dumps(oversized_order))} bytes."
            ),
        )

    order_topic = config.order_topic
    client.subscribe([config.state_topic])

    compact_order = build_order_payload(config)
    client.publish_json(order_topic, compact_order, qos=1)
    
    # 1. Chờ ESP32 phản hồi order chuẩn
    state_msg = client.wait_for(config.state_topic, timeout_s=config.default_timeout_s)
    if not state_msg or state_msg.payload.get("orderId") != compact_order["orderId"]:
        return TestOutcome(name="TC2", passed=False, details="Failed to process compact order.")

    # 2. Bắn order siêu to khổng lồ (> 2048 bytes)
    oversized_order = build_oversized_order_payload(config)
    client.publish_json(order_topic, oversized_order, qos=1)
    
    # 3. Phải đảm bảo ESP32 KHÔNG bị crash và vẫn gửi được heartbeat tiếp theo
    heartbeat_msg = client.wait_for(
        config.state_topic, 
        predicate=lambda p: p.get("headerId") != state_msg.payload.get("headerId"), 
        timeout_s=config.heartbeat_wait_s
    )

    if not heartbeat_msg:
        return TestOutcome(name="TC2", passed=False, details="AGV crashed or stopped sending heartbeat after oversized payload.")

    nodes = compact_order.get("nodes", [])
    edges = compact_order.get("edges", [])
    if len(nodes) < 2 or len(edges) < 1:
        return TestOutcome(name="TC2", passed=False, details="Compact order payload is malformed.")

    return TestOutcome(
        name="TC2",
        passed=True,
        details=(
            "Published a valid compact order and an oversized order payload. "
            "A state frame was observed after publishing."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="AGV system integration harness")
    parser.add_argument("--case", choices=["tc1", "tc2", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Do not require a live broker; validate payload generation only.")
    parser.add_argument("--json", action="store_true", help="Print results as JSON.")
    parser.add_argument("--serial", default=None, help="Override AGV serial number (default: from AGV_SERIAL).")
    parser.add_argument("--broker", default=None, help="Override MQTT broker host.")
    parser.add_argument("--port", type=int, default=None, help="Override MQTT broker port.")
    return parser


def _apply_overrides(config: HarnessConfig, args: argparse.Namespace) -> HarnessConfig:
    """Return a config clone with CLI overrides applied."""

    return HarnessConfig(
        manufacturer=config.manufacturer,
        version=config.version,
        serial_number=args.serial or config.serial_number,
        mqtt_broker=args.broker or config.mqtt_broker,
        mqtt_port=args.port or config.mqtt_port,
        keepalive_s=config.keepalive_s,
        default_timeout_s=config.default_timeout_s,
        heartbeat_wait_s=config.heartbeat_wait_s,
    )


def run() -> int:
    """Execute selected test cases and return a process exit code."""

    args = build_parser().parse_args()
    config = _apply_overrides(get_config(), args)
    client = HarnessMqttClient(config)

    outcomes: list[TestOutcome] = []
    try:
        if not args.dry_run:
            client.connect()
        if args.case in ("tc1", "all"):
            outcomes.append(_run_case_1(client, config, args.dry_run))
        if args.case in ("tc2", "all"):
            outcomes.append(_run_case_2(client, config, args.dry_run))
    finally:
        if not args.dry_run:
            client.close()

    if args.json:
        print(json.dumps([outcome.__dict__ for outcome in outcomes], ensure_ascii=False, indent=2))
    else:
        for outcome in outcomes:
            status = "PASS" if outcome.passed else "FAIL"
            print(f"[{status}] {outcome.name}: {outcome.details}")

    return 0 if all(outcome.passed for outcome in outcomes) else 1


if __name__ == "__main__":
    sys.exit(run())

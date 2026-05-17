"""Server-side deadlock/stuck monitor service."""

from __future__ import annotations

import time
import uuid
from typing import Optional

from django.utils import timezone

from vda5050.models import DeadlockEvent, Order


class DeadlockMonitorService:
    """Track AGV state stream and emit potential deadlock events."""

    def __init__(
        self, stuck_threshold_s: float = 45.0, position_epsilon_m: float = 0.2
    ):
        self.stuck_threshold_s = stuck_threshold_s
        self.position_epsilon_m = position_epsilon_m
        self._snapshots: dict[str, dict] = {}

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _is_order_active(self, agv, order_id: str) -> bool:
        if not order_id:
            return False
        return Order.objects.filter(
            agv=agv,
            order_id=order_id,
            status__in=[
                Order.OrderStatus.SENT,
                Order.OrderStatus.ACTIVE,
                Order.OrderStatus.QUEUED,
            ],
        ).exists()

    def _resolve_open_potential(self, agv, order_id: str, reason: str) -> None:
        if not order_id:
            return

        open_event = (
            DeadlockEvent.objects.filter(
                agv=agv,
                order_id=order_id,
                status=DeadlockEvent.Status.POTENTIAL,
            )
            .order_by("-detected_at")
            .first()
        )
        if not open_event:
            return

        open_event.status = DeadlockEvent.Status.RESOLVED
        open_event.resolved_at = timezone.now()
        details = dict(open_event.details or {})
        details["resolved_reason"] = reason
        open_event.details = details
        open_event.last_seen_at = timezone.now()
        open_event.save(
            update_fields=["status", "resolved_at", "details", "last_seen_at"]
        )

    def _upsert_potential_event(
        self,
        agv,
        order_id: str,
        node_id: str,
        sequence_id: int,
        x: float,
        y: float,
        stuck_duration_s: float,
    ) -> tuple[DeadlockEvent, bool]:
        now = timezone.now()
        open_event = (
            DeadlockEvent.objects.filter(
                agv=agv,
                order_id=order_id,
                status=DeadlockEvent.Status.POTENTIAL,
            )
            .order_by("-detected_at")
            .first()
        )

        if open_event:
            open_event.node_id = node_id
            open_event.sequence_id = sequence_id
            open_event.position = {"x": round(x, 3), "y": round(y, 3)}
            open_event.stuck_duration_s = round(stuck_duration_s, 2)
            details = dict(open_event.details or {})
            details["monitor"] = "phase1"
            details["threshold_s"] = self.stuck_threshold_s
            open_event.details = details
            open_event.last_seen_at = now
            open_event.save(
                update_fields=[
                    "node_id",
                    "sequence_id",
                    "position",
                    "stuck_duration_s",
                    "details",
                    "last_seen_at",
                ]
            )
            return open_event, False

        event = DeadlockEvent.objects.create(
            event_id=f"DLK_{uuid.uuid4().hex[:10].upper()}",
            agv=agv,
            order_id=order_id,
            node_id=node_id,
            sequence_id=sequence_id,
            position={"x": round(x, 3), "y": round(y, 3)},
            agv_set=[agv.serial_number],
            conflicted_resources=[node_id] if node_id else [],
            stuck_duration_s=round(stuck_duration_s, 2),
            status=DeadlockEvent.Status.POTENTIAL,
            details={
                "monitor": "phase1",
                "threshold_s": self.stuck_threshold_s,
                "position_epsilon_m": self.position_epsilon_m,
            },
            last_seen_at=now,
        )
        return event, True

    def process_state(self, agv, state, order_id: Optional[str]) -> Optional[dict]:
        """Process one AGV state packet and emit potential deadlock events.

        Returns:
            None when no stuck event is detected, otherwise a dict with event metadata.
        """
        serial = agv.serial_number
        now_ts = time.time()

        current_order_id = order_id or ""
        current_node = state.last_node_id or ""
        current_seq = int(state.last_node_sequence_id or 0)
        position = state.agv_position or {}
        x = self._safe_float(position.get("x"), 0.0)
        y = self._safe_float(position.get("y"), 0.0)
        driving = bool(state.driving)
        order_active = self._is_order_active(agv, current_order_id)

        prev = self._snapshots.get(serial)

        if not current_order_id:
            if prev:
                self._resolve_open_potential(
                    agv, prev.get("order_id", ""), "order_cleared"
                )
                self._snapshots.pop(serial, None)
            return None

        same_order = bool(prev) and prev.get("order_id") == current_order_id
        same_seq = bool(prev) and prev.get("sequence_id") == current_seq
        dx = (x - prev.get("x", x)) if prev else 0.0
        dy = (y - prev.get("y", y)) if prev else 0.0
        same_position = (dx * dx + dy * dy) ** 0.5 <= self.position_epsilon_m
        blocked_like = driving or order_active

        if same_order and same_seq and same_position and blocked_like:
            stuck_duration = now_ts - prev["since_ts"]
            self._snapshots[serial]["last_seen_ts"] = now_ts
            self._snapshots[serial]["node_id"] = current_node
            self._snapshots[serial]["x"] = x
            self._snapshots[serial]["y"] = y

            if stuck_duration >= self.stuck_threshold_s:
                event, created = self._upsert_potential_event(
                    agv=agv,
                    order_id=current_order_id,
                    node_id=current_node,
                    sequence_id=current_seq,
                    x=x,
                    y=y,
                    stuck_duration_s=stuck_duration,
                )
                return {
                    "event_id": event.event_id,
                    "created": created,
                    "stuck_duration_s": round(stuck_duration, 2),
                    "order_id": current_order_id,
                    "node_id": current_node,
                    "sequence_id": current_seq,
                }
            return None

        if prev and prev.get("order_id"):
            self._resolve_open_potential(
                agv, prev.get("order_id", ""), "state_progressed"
            )

        self._snapshots[serial] = {
            "order_id": current_order_id,
            "node_id": current_node,
            "sequence_id": current_seq,
            "x": x,
            "y": y,
            "driving": driving,
            "since_ts": now_ts,
            "last_seen_ts": now_ts,
        }
        return None

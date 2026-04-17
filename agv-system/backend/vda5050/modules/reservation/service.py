from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from django.db.models import Q
from django.utils import timezone

from vda5050.models import EdgeReservation, NodeReservation


@dataclass
class ConflictResult:
    has_conflict: bool
    node_ids: list[str]
    edge_ids: list[str]
    node_conflicts: list[dict]
    edge_conflicts: list[dict]


class ReservationService:
    """Manage node/edge time-window reservations and conflict checks."""

    ACTIVE_STATUSES = [
        NodeReservation.Status.RESERVED,
    ]

    EDGE_ACTIVE_STATUSES = [
        EdgeReservation.Status.RESERVED,
    ]

    def __init__(
        self,
        default_node_window_s: float = 5.0,
        min_edge_window_s: float = 3.0,
        fallback_speed_mps: float = 1.0,
        reservation_padding_s: float = 1.0,
    ):
        self.default_node_window_s = default_node_window_s
        self.min_edge_window_s = min_edge_window_s
        self.fallback_speed_mps = max(fallback_speed_mps, 0.1)
        self.reservation_padding_s = reservation_padding_s

    @staticmethod
    def _safe_float(value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _build_schedule(self, nodes: list[dict], edges: list[dict], start_at=None) -> dict:
        now = start_at or timezone.now()
        schedule_nodes: list[dict] = []
        schedule_edges: list[dict] = []

        cursor = now
        edge_by_start = {edge.get("startNodeId"): edge for edge in edges}

        for idx, node in enumerate(nodes):
            node_id = node.get("nodeId")
            if not node_id:
                continue

            node_start = cursor
            node_end = node_start + timedelta(seconds=self.default_node_window_s)
            schedule_nodes.append(
                {
                    "node_id": node_id,
                    "sequence_id": int(node.get("sequenceId", idx * 2)),
                    "t_start": node_start,
                    "t_end": node_end,
                }
            )
            cursor = node_end

            edge = edge_by_start.get(node_id)
            if not edge:
                continue

            start_node = edge.get("startNodeId")
            end_node = edge.get("endNodeId")
            if not start_node or not end_node:
                continue

            max_speed = self._safe_float(edge.get("maxSpeed"), self.fallback_speed_mps)
            travel_window = max(self.min_edge_window_s, 1.0 / max(max_speed, 0.1))
            edge_start = cursor
            edge_end = edge_start + timedelta(seconds=travel_window + self.reservation_padding_s)

            schedule_edges.append(
                {
                    "edge_id": edge.get("edgeId") or f"{start_node}_{end_node}",
                    "start_node_id": start_node,
                    "end_node_id": end_node,
                    "sequence_id": int(edge.get("sequenceId", idx * 2 + 1)),
                    "t_start": edge_start,
                    "t_end": edge_end,
                }
            )
            cursor = edge_end

        return {"nodes": schedule_nodes, "edges": schedule_edges}

    @staticmethod
    def _overlap_query(start_field: str, end_field: str, t_start, t_end) -> Q:
        return Q(**{f"{start_field}__lt": t_end, f"{end_field}__gt": t_start})

    def _build_node_conflicts(
        self,
        schedule_nodes: Iterable[dict],
        agv_id: int,
    ) -> list[dict]:
        conflicts = []
        for item in schedule_nodes:
            qs = NodeReservation.objects.filter(
                node_id=item["node_id"],
                status__in=self.ACTIVE_STATUSES,
            ).exclude(agv_id=agv_id)
            qs = qs.filter(self._overlap_query("t_start", "t_end", item["t_start"], item["t_end"]))

            reservation = qs.order_by("t_start").first()
            if reservation:
                conflicts.append(
                    {
                        "node_id": item["node_id"],
                        "sequence_id": item["sequence_id"],
                        "t_start": item["t_start"],
                        "t_end": item["t_end"],
                        "conflict_with_agv": reservation.agv.serial_number,
                        "conflict_order_id": reservation.order.order_id if reservation.order else None,
                    }
                )
        return conflicts

    def _build_edge_conflicts(
        self,
        schedule_edges: Iterable[dict],
        agv_id: int,
    ) -> list[dict]:
        conflicts = []
        for item in schedule_edges:
            qs = EdgeReservation.objects.filter(
                edge_id=item["edge_id"],
                status__in=self.EDGE_ACTIVE_STATUSES,
            ).exclude(agv_id=agv_id)
            qs = qs.filter(self._overlap_query("t_start", "t_end", item["t_start"], item["t_end"]))

            reservation = qs.order_by("t_start").first()
            if reservation:
                conflicts.append(
                    {
                        "edge_id": item["edge_id"],
                        "start_node_id": item["start_node_id"],
                        "end_node_id": item["end_node_id"],
                        "sequence_id": item["sequence_id"],
                        "t_start": item["t_start"],
                        "t_end": item["t_end"],
                        "conflict_with_agv": reservation.agv.serial_number,
                        "conflict_order_id": reservation.order.order_id if reservation.order else None,
                    }
                )

            reverse_qs = EdgeReservation.objects.filter(
                start_node_id=item["end_node_id"],
                end_node_id=item["start_node_id"],
                status__in=self.EDGE_ACTIVE_STATUSES,
            ).exclude(agv_id=agv_id)
            reverse_qs = reverse_qs.filter(
                self._overlap_query("t_start", "t_end", item["t_start"], item["t_end"])
            )

            reverse_reservation = reverse_qs.order_by("t_start").first()
            if reverse_reservation:
                conflicts.append(
                    {
                        "edge_id": item["edge_id"],
                        "start_node_id": item["start_node_id"],
                        "end_node_id": item["end_node_id"],
                        "sequence_id": item["sequence_id"],
                        "t_start": item["t_start"],
                        "t_end": item["t_end"],
                        "conflict_with_agv": reverse_reservation.agv.serial_number,
                        "conflict_order_id": (
                            reverse_reservation.order.order_id if reverse_reservation.order else None
                        ),
                        "reason": "head_on_reverse_edge",
                    }
                )
        return conflicts

    def detect_conflicts(self, agv, nodes: list[dict], edges: list[dict]) -> ConflictResult:
        schedule = self._build_schedule(nodes=nodes, edges=edges)
        node_conflicts = self._build_node_conflicts(schedule["nodes"], agv_id=agv.id)
        edge_conflicts = self._build_edge_conflicts(schedule["edges"], agv_id=agv.id)

        node_ids = sorted({item["node_id"] for item in node_conflicts})
        edge_ids = sorted({item["edge_id"] for item in edge_conflicts})

        return ConflictResult(
            has_conflict=bool(node_conflicts or edge_conflicts),
            node_ids=node_ids,
            edge_ids=edge_ids,
            node_conflicts=node_conflicts,
            edge_conflicts=edge_conflicts,
        )

    def persist_reservations(self, order) -> None:
        schedule = self._build_schedule(nodes=order.nodes or [], edges=order.edges or [])

        node_rows = [
            NodeReservation(
                node_id=item["node_id"],
                agv=order.agv,
                order=order,
                t_start=item["t_start"],
                t_end=item["t_end"],
                status=NodeReservation.Status.RESERVED,
                details={"sequence_id": item["sequence_id"]},
            )
            for item in schedule["nodes"]
        ]
        if node_rows:
            NodeReservation.objects.bulk_create(node_rows)

        edge_rows = [
            EdgeReservation(
                edge_id=item["edge_id"],
                start_node_id=item["start_node_id"],
                end_node_id=item["end_node_id"],
                agv=order.agv,
                order=order,
                t_start=item["t_start"],
                t_end=item["t_end"],
                status=EdgeReservation.Status.RESERVED,
                details={"sequence_id": item["sequence_id"]},
            )
            for item in schedule["edges"]
        ]
        if edge_rows:
            EdgeReservation.objects.bulk_create(edge_rows)

    def release_order_reservations(self, order, reason: str = "order_done") -> None:
        now = timezone.now()
        NodeReservation.objects.filter(
            order=order,
            status=NodeReservation.Status.RESERVED,
        ).update(status=NodeReservation.Status.RELEASED, t_end=now, details={"reason": reason})

        EdgeReservation.objects.filter(
            order=order,
            status=EdgeReservation.Status.RESERVED,
        ).update(status=EdgeReservation.Status.RELEASED, t_end=now, details={"reason": reason})

    def expire_old_reservations(self) -> None:
        now = timezone.now()
        NodeReservation.objects.filter(
            status=NodeReservation.Status.RESERVED,
            t_end__lt=now,
        ).update(status=NodeReservation.Status.EXPIRED)

        EdgeReservation.objects.filter(
            status=EdgeReservation.Status.RESERVED,
            t_end__lt=now,
        ).update(status=EdgeReservation.Status.EXPIRED)

    @staticmethod
    def apply_horizon_release(
        nodes: list[dict],
        edges: list[dict],
        conflict_node_ids: list[str],
        conflict_edge_ids: list[str],
    ) -> tuple[list[dict], list[dict], int | None]:
        sequence_candidates = []
        for node in nodes:
            if node.get("nodeId") in conflict_node_ids:
                sequence_candidates.append(int(node.get("sequenceId", 0)))
        for edge in edges:
            edge_id = edge.get("edgeId")
            if edge_id in conflict_edge_ids:
                sequence_candidates.append(int(edge.get("sequenceId", 0)))

        if not sequence_candidates:
            return nodes, edges, None

        cut_seq = min(sequence_candidates)
        max_sequence = 0
        if nodes:
            max_sequence = max(max_sequence, max(int(n.get("sequenceId", 0)) for n in nodes))
        if edges:
            max_sequence = max(max_sequence, max(int(e.get("sequenceId", 0)) for e in edges))

        # Bootstrap release to avoid AGVs being locked at sequence=0 forever.
        bootstrap_release_seq = min(3, max_sequence)
        release_upto_seq = max(cut_seq - 1, bootstrap_release_seq)

        new_nodes = []
        for node in nodes:
            node_copy = dict(node)
            node_seq = int(node_copy.get("sequenceId", 0))
            node_copy["released"] = node_seq <= release_upto_seq
            new_nodes.append(node_copy)

        new_edges = []
        for edge in edges:
            edge_copy = dict(edge)
            edge_seq = int(edge_copy.get("sequenceId", 0))
            edge_copy["released"] = edge_seq <= release_upto_seq
            new_edges.append(edge_copy)

        # Ensure at least one edge can be traversed from current node.
        if new_edges and not any(bool(edge.get("released")) for edge in new_edges):
            first_edge = min(new_edges, key=lambda item: int(item.get("sequenceId", 10**9)))
            first_edge["released"] = True
            first_edge_seq = int(first_edge.get("sequenceId", 0))
            for node in new_nodes:
                if int(node.get("sequenceId", 0)) <= first_edge_seq + 1:
                    node["released"] = True

        return new_nodes, new_edges, cut_seq

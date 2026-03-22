"""
Metrics Collector for AGV Simulation.

Collects and exports scientific data:
- Per-order metrics: flow time, energy consumed, distance, wait time
- Per-AGV metrics: total tasks, utilization, battery history
- Fleet-level metrics: load balance, total flow time, makespan

Outputs to CSV files for analysis.
"""

import csv
import json
import os
import time
import threading
import logging
from datetime import datetime
from collections import defaultdict
from typing import Optional

import paho.mqtt.client as mqtt

from config_sim import MQTT_BROKER, MQTT_PORT, MANUFACTURER

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects metrics from AGV simulation via callbacks and MQTT monitoring.
    Exports results to CSV files.
    """

    def __init__(self, output_dir: str = "results", scenario_name: str = "default"):
        self.scenario_name = scenario_name
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Order-level metrics
        self.order_records: list[dict] = []

        # AGV-level tracking
        self.agv_task_count: dict[str, int] = defaultdict(int)
        self.agv_total_flow_time: dict[str, float] = defaultdict(float)
        self.agv_total_energy: dict[str, float] = defaultdict(float)
        self.agv_total_distance: dict[str, float] = defaultdict(float)
        self.agv_total_wait_time: dict[str, float] = defaultdict(float)
        self.agv_battery_history: dict[str, list] = defaultdict(list)

        # Task dispatch tracking (from server API)
        self.task_assignments: list[dict] = []

        # Bidding execution time (ms)
        self.bidding_times_ms: list[float] = []

        # Deadlock tracking
        self.deadlock_count: int = 0
        self._deadlock_check_states: dict[str, dict] = {}  # agv -> {node, timestamp}

        # Fleet-level
        self._simulation_start: float = 0.0
        self._simulation_end: float = 0.0
        self._first_task_dispatched: float = 0.0
        self._last_order_completed: float = 0.0

        # Thread safety
        self._lock = threading.Lock()

        # MQTT client for monitoring state messages
        self._mqtt_client: Optional[mqtt.Client] = None

        logger.info(f"MetricsCollector initialized: scenario={scenario_name}, output={output_dir}")

    # ==================== Data Collection ====================

    def start_simulation_timer(self):
        """Call when simulation begins."""
        self._simulation_start = time.time()

    def stop_simulation_timer(self):
        """Call when simulation ends."""
        self._simulation_end = time.time()

    def record_order_complete(self, metrics: dict):
        """
        Record completion of a single order.
        Called by AdvancedMockAGV.on_order_complete callback.

        Expected keys: agv, order_id, flow_time_s, energy_consumed_pct,
                       distance_m, wait_time_s, move_time_s, battery_remaining_pct
        """
        with self._lock:
            self.order_records.append(metrics)

            agv = metrics["agv"]
            self.agv_task_count[agv] += 1
            self.agv_total_flow_time[agv] += metrics.get("flow_time_s", 0)
            self.agv_total_energy[agv] += metrics.get("energy_consumed_pct", 0)
            self.agv_total_distance[agv] += metrics.get("distance_m", 0)
            self.agv_total_wait_time[agv] += metrics.get("wait_time_s", 0)
            self._last_order_completed = time.time()

        logger.info(
            f"[Metrics] Order {metrics.get('order_id', '?')} completed by {agv} | "
            f"Flow: {metrics.get('flow_time_s', 0):.1f}s | "
            f"Energy: {metrics.get('energy_consumed_pct', 0):.2f}%"
        )

    def record_task_assignment(self, task_info: dict):
        """
        Record a task assignment from the server.

        Expected keys: order_id, winner_agv, pickup_node, delivery_node,
                       timestamp, bidding_time_ms
        """
        with self._lock:
            self.task_assignments.append(task_info)
            if "bidding_time_ms" in task_info:
                self.bidding_times_ms.append(task_info["bidding_time_ms"])
            # Track first dispatch time for true makespan
            if self._first_task_dispatched == 0.0:
                self._first_task_dispatched = time.time()

    def record_battery_snapshot(self, agv: str, battery: float, timestamp: str):
        """Record battery level at a point in time."""
        with self._lock:
            self.agv_battery_history[agv].append(
                {"timestamp": timestamp, "battery": battery}
            )

    # ==================== MQTT Monitoring ====================

    def start_mqtt_monitor(self, agv_serials: list[str]):
        """Subscribe to AGV state topics to monitor battery in real-time."""
        self._mqtt_client = mqtt.Client(
            client_id=f"metrics_{self.scenario_name}_{id(self) % 10000}"
        )
        self._mqtt_client.on_message = self._on_mqtt_message
        self._mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

        for serial in agv_serials:
            topic = f"uagv/v2/{MANUFACTURER}/{serial}/state"
            self._mqtt_client.subscribe(topic, 0)

        self._mqtt_client.loop_start()
        logger.info(f"[Metrics] MQTT monitor started for {len(agv_serials)} AGVs")

    def stop_mqtt_monitor(self):
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            parts = msg.topic.split("/")
            if len(parts) >= 5:
                serial = parts[3]
                battery = payload.get("batteryState", {}).get("batteryCharge", 0)
                ts = payload.get("timestamp", "")
                self.record_battery_snapshot(serial, battery, ts)
                # Deadlock detection: check if AGV is stuck at same node for too long
                self._check_deadlock(serial, payload)
        except Exception:
            pass

    def _check_deadlock(self, serial: str, payload: dict):
        """Detect potential deadlocks: AGV stuck at same node while driving."""
        node = payload.get("lastNodeId", "")
        driving = payload.get("driving", False)
        now = time.time()

        prev = self._deadlock_check_states.get(serial)
        if prev and driving and prev.get("driving") and prev["node"] == node:
            # Same node, still marked driving -> stuck
            stuck_duration = now - prev["since"]
            if stuck_duration > 60:  # 60s threshold
                if not prev.get("reported"):
                    self.deadlock_count += 1
                    self._deadlock_check_states[serial]["reported"] = True
                    logger.warning(
                        f"[Metrics] Potential deadlock: {serial} stuck at {node} "
                        f"for {stuck_duration:.0f}s"
                    )
        else:
            self._deadlock_check_states[serial] = {
                "node": node, "driving": driving, "since": now, "reported": False
            }

    # ==================== Export ====================

    def export_all(self) -> dict[str, str]:
        """
        Export all collected metrics to CSV files.
        Returns dict of {metric_name: file_path}.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{self.scenario_name}_{timestamp}"
        files = {}

        files["orders"] = self._export_order_metrics(prefix)
        files["agv_summary"] = self._export_agv_summary(prefix)
        files["load_balance"] = self._export_load_balance(prefix)
        files["task_assignments"] = self._export_task_assignments(prefix)
        files["fleet_summary"] = self._export_fleet_summary(prefix)

        logger.info(f"[Metrics] Exported {len(files)} files to {self.output_dir}/")
        return files

    def _export_order_metrics(self, prefix: str) -> str:
        """Export per-order metrics."""
        filepath = os.path.join(self.output_dir, f"{prefix}_orders.csv")
        headers = [
            "agv",
            "order_id",
            "flow_time_s",
            "energy_consumed_pct",
            "distance_m",
            "wait_time_s",
            "move_time_s",
            "battery_remaining_pct",
            "timestamp",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for record in self.order_records:
                writer.writerow(record)

        logger.info(f"  -> {filepath} ({len(self.order_records)} orders)")
        return filepath

    def _export_agv_summary(self, prefix: str) -> str:
        """Export per-AGV aggregated metrics."""
        filepath = os.path.join(self.output_dir, f"{prefix}_agv_summary.csv")
        headers = [
            "agv",
            "tasks_completed",
            "total_flow_time_s",
            "total_energy_pct",
            "total_distance_m",
            "total_wait_time_s",
            "avg_flow_time_s",
            "avg_energy_pct",
        ]

        all_agvs = sorted(
            set(self.agv_task_count.keys())
            | set(self.agv_total_flow_time.keys())
        )

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for agv in all_agvs:
                count = self.agv_task_count.get(agv, 0)
                writer.writerow(
                    {
                        "agv": agv,
                        "tasks_completed": count,
                        "total_flow_time_s": round(self.agv_total_flow_time.get(agv, 0), 2),
                        "total_energy_pct": round(self.agv_total_energy.get(agv, 0), 3),
                        "total_distance_m": round(self.agv_total_distance.get(agv, 0), 2),
                        "total_wait_time_s": round(self.agv_total_wait_time.get(agv, 0), 2),
                        "avg_flow_time_s": round(
                            self.agv_total_flow_time.get(agv, 0) / max(count, 1), 2
                        ),
                        "avg_energy_pct": round(
                            self.agv_total_energy.get(agv, 0) / max(count, 1), 3
                        ),
                    }
                )

        logger.info(f"  -> {filepath} ({len(all_agvs)} AGVs)")
        return filepath

    def _export_load_balance(self, prefix: str) -> str:
        """Export load balancing analysis."""
        filepath = os.path.join(self.output_dir, f"{prefix}_load_balance.csv")

        all_agvs = sorted(self.agv_task_count.keys())
        counts = [self.agv_task_count.get(a, 0) for a in all_agvs]
        total = sum(counts)
        mean = total / max(len(counts), 1)

        # Coefficient of Variation (CV) - lower is more balanced
        if mean > 0 and len(counts) > 1:
            variance = sum((c - mean) ** 2 for c in counts) / len(counts)
            std_dev = variance ** 0.5
            cv = std_dev / mean
        else:
            std_dev = 0
            cv = 0

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            writer.writerow(["total_tasks", total])
            writer.writerow(["num_agvs", len(all_agvs)])
            writer.writerow(["mean_tasks_per_agv", round(mean, 2)])
            writer.writerow(["std_dev_tasks", round(std_dev, 2)])
            writer.writerow(["cv_tasks", round(cv, 4)])
            # CV of distance
            distances = [self.agv_total_distance.get(a, 0) for a in all_agvs]
            d_mean = sum(distances) / max(len(distances), 1)
            if d_mean > 0 and len(distances) > 1:
                d_var = sum((d - d_mean) ** 2 for d in distances) / len(distances)
                cv_dist = (d_var ** 0.5) / d_mean
            else:
                cv_dist = 0
            writer.writerow(["cv_distance", round(cv_dist, 4)])
            writer.writerow(["min_tasks", min(counts) if counts else 0])
            writer.writerow(["max_tasks", max(counts) if counts else 0])
            writer.writerow(["deadlock_count", self.deadlock_count])
            writer.writerow([])
            writer.writerow(["agv", "tasks_completed", "distance_m"])
            for agv in all_agvs:
                writer.writerow([
                    agv,
                    self.agv_task_count.get(agv, 0),
                    round(self.agv_total_distance.get(agv, 0), 2),
                ])

        logger.info(f"  -> {filepath} (CV={cv:.4f})")
        return filepath

    def _export_task_assignments(self, prefix: str) -> str:
        """Export task assignment history."""
        filepath = os.path.join(self.output_dir, f"{prefix}_assignments.csv")
        headers = [
            "order_id", "winner_agv", "pickup_node", "delivery_node",
            "bidding_time_ms", "timestamp",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for record in self.task_assignments:
                writer.writerow(record)

        logger.info(f"  -> {filepath} ({len(self.task_assignments)} assignments)")
        return filepath

    def _export_fleet_summary(self, prefix: str) -> str:
        """Export fleet-level summary."""
        filepath = os.path.join(self.output_dir, f"{prefix}_fleet_summary.csv")

        sim_duration = self._simulation_end - self._simulation_start if self._simulation_end else 0
        total_tasks = sum(self.agv_task_count.values())
        total_flow_time = sum(self.agv_total_flow_time.values())
        total_energy = sum(self.agv_total_energy.values())
        total_distance = sum(self.agv_total_distance.values())
        total_wait = sum(self.agv_total_wait_time.values())

        # Makespan = wall-clock from first dispatch to last order completed
        if self._first_task_dispatched > 0 and self._last_order_completed > 0:
            makespan = self._last_order_completed - self._first_task_dispatched
        else:
            makespan = sim_duration

        # Energy per task
        energy_per_task = total_energy / max(total_tasks, 1)

        # CV of distance
        distances = [self.agv_total_distance.get(a, 0) for a in self.agv_task_count.keys()]
        if distances and len(distances) > 1:
            d_mean = sum(distances) / len(distances)
            d_var = sum((d - d_mean) ** 2 for d in distances) / len(distances)
            cv_distance = (d_var ** 0.5) / d_mean if d_mean > 0 else 0
        else:
            cv_distance = 0

        # Bidding time stats
        if self.bidding_times_ms:
            avg_bid_ms = sum(self.bidding_times_ms) / len(self.bidding_times_ms)
            max_bid_ms = max(self.bidding_times_ms)
            min_bid_ms = min(self.bidding_times_ms)
        else:
            avg_bid_ms = max_bid_ms = min_bid_ms = 0

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            # --- Scenario ---
            writer.writerow(["scenario", self.scenario_name])
            writer.writerow(["num_agvs", len(self.agv_task_count)])
            # --- Time & Efficiency ---
            writer.writerow(["simulation_duration_s", round(sim_duration, 2)])
            writer.writerow(["makespan_s", round(makespan, 2)])
            writer.writerow(["total_tasks_completed", total_tasks])
            writer.writerow(["total_flow_time_s", round(total_flow_time, 2)])
            writer.writerow(["avg_flow_time_per_task_s", round(total_flow_time / max(total_tasks, 1), 2)])
            writer.writerow(["total_wait_time_s", round(total_wait, 2)])
            writer.writerow(["throughput_tasks_per_min", round(total_tasks / max(sim_duration / 60, 0.01), 2)])
            # --- Energy ---
            writer.writerow(["total_energy_consumed_pct", round(total_energy, 3)])
            writer.writerow(["energy_per_task_pct", round(energy_per_task, 3)])
            writer.writerow(["total_distance_m", round(total_distance, 2)])
            # --- Load Balance & Robustness ---
            writer.writerow(["cv_distance", round(cv_distance, 4)])
            writer.writerow(["deadlock_count", self.deadlock_count])
            # --- Algorithm Overhead ---
            writer.writerow(["avg_bidding_time_ms", round(avg_bid_ms, 2)])
            writer.writerow(["max_bidding_time_ms", round(max_bid_ms, 2)])
            writer.writerow(["min_bidding_time_ms", round(min_bid_ms, 2)])
            writer.writerow(["makespan_s", round(makespan, 2)])
            writer.writerow(["total_energy_consumed_pct", round(total_energy, 3)])
            writer.writerow(["total_distance_m", round(total_distance, 2)])
            writer.writerow(["total_wait_time_s", round(total_wait, 2)])
            writer.writerow(["avg_flow_time_per_task_s", round(total_flow_time / max(total_tasks, 1), 2)])
            writer.writerow(["min_bidding_time_ms", round(min_bid_ms, 2)])

        logger.info(f"  -> {filepath}")
        return filepath

    # ==================== Console Report ====================

    def print_summary(self):
        """Print a formatted summary to console."""
        sim_duration = self._simulation_end - self._simulation_start if self._simulation_end else 0
        total_tasks = sum(self.agv_task_count.values())
        total_flow = sum(self.agv_total_flow_time.values())
        total_energy = sum(self.agv_total_energy.values())
        total_wait = sum(self.agv_total_wait_time.values())

        # True makespan
        if self._first_task_dispatched > 0 and self._last_order_completed > 0:
            makespan = self._last_order_completed - self._first_task_dispatched
        else:
            makespan = sim_duration

        print(f"\n{'=' * 70}")
        print(f"  SIMULATION RESULTS - Scenario: {self.scenario_name}")
        print(f"{'=' * 70}")

        # 1. Time & Efficiency
        print(f"  [Time & Efficiency]")
        print(f"    Makespan:           {makespan:.1f}s")
        print(f"    Total Flow Time:    {total_flow:.1f}s")
        print(f"    Avg Flow/Task:      {total_flow / max(total_tasks, 1):.1f}s")
        print(f"    Total Wait Time:    {total_wait:.1f}s")
        print(f"    Throughput:         {total_tasks / max(sim_duration / 60, 0.01):.2f} tasks/min")

        # 2. Energy
        print(f"  [Energy]")
        print(f"    Total Energy:       {total_energy:.3f}%")
        print(f"    Energy/Task:        {total_energy / max(total_tasks, 1):.3f}%")

        # 3. Algorithm Overhead
        if self.bidding_times_ms:
            avg_bid = sum(self.bidding_times_ms) / len(self.bidding_times_ms)
            print(f"  [Algorithm Overhead]")
            print(f"    Avg Bidding Time:   {avg_bid:.1f} ms")
            print(f"    Max Bidding Time:   {max(self.bidding_times_ms):.1f} ms")
            print(f"    Min Bidding Time:   {min(self.bidding_times_ms):.1f} ms")

        print(f"{'─' * 70}")
        print(f"  {'AGV':<10} {'Tasks':>6} {'FlowTime':>10} {'Energy':>8} {'Distance':>10} {'Wait':>8}")
        print(f"  {'─' * 56}")

        for agv in sorted(self.agv_task_count.keys()):
            cnt = self.agv_task_count[agv]
            print(
                f"  {agv:<10} {cnt:>6} "
                f"{self.agv_total_flow_time.get(agv, 0):>9.1f}s "
                f"{self.agv_total_energy.get(agv, 0):>7.2f}% "
                f"{self.agv_total_distance.get(agv, 0):>9.1f}m "
                f"{self.agv_total_wait_time.get(agv, 0):>7.1f}s"
            )

        # 4. Load Balance & Robustness
        counts = list(self.agv_task_count.values())
        if counts:
            mean = sum(counts) / len(counts)
            variance = sum((c - mean) ** 2 for c in counts) / len(counts)
            cv_tasks = (variance ** 0.5) / mean if mean > 0 else 0
            distances = list(self.agv_total_distance.values())
            d_mean = sum(distances) / len(distances)
            d_var = sum((d - d_mean) ** 2 for d in distances) / len(distances)
            cv_dist = (d_var ** 0.5) / d_mean if d_mean > 0 else 0
            print(f"{'─' * 70}")
            print(f"  [Load Balance & Robustness]")
            print(f"    CV (Tasks):    {cv_tasks:.4f}  (0=perfect, <0.3=good, >0.5=poor)")
            print(f"    CV (Distance): {cv_dist:.4f}")
            print(f"    Deadlock Count: {self.deadlock_count}")

        print(f"{'=' * 70}\n")

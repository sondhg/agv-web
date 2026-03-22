"""
Multi-Agent Runner - Orchestrates AGV simulation with scenarios.

Usage:
    python multi_agent_runner.py                     # Run basic scenario
    python multi_agent_runner.py --scenario burst    # Run specific scenario
    python multi_agent_runner.py --scenario all      # Run all scenarios
    python multi_agent_runner.py --list              # List scenarios
    python multi_agent_runner.py --agvs 5            # Custom fleet size (basic scenario)
"""

import argparse
import logging
import time
import requests
from datetime import datetime, timezone

from advanced_mock_agv import AdvancedMockAGV
from metrics_collector import MetricsCollector
from scenarios import ALL_SCENARIOS, get_scenario, list_scenarios
from config_sim import (
    API_BASE_URL,
    STATUS_PRINT_INTERVAL,
    generate_fleet,
)

# ==================== Logging ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class SimulationRunner:
    """
    Orchestrates a complete simulation:
    1. Start AGV fleet
    2. Dispatch tasks via server API
    3. Collect metrics
    4. Export results
    """

    def __init__(self, scenario: dict, epsilon: float = None):
        self.scenario = scenario
        self.name = scenario["name"]
        self.fleet_config = scenario["fleet"]
        self.tasks = scenario["tasks"]
        self.timeout = scenario.get("timeout_s", 300)
        self.epsilon = epsilon

        # Include epsilon in output directory name for easy comparison
        suffix = f"_eps{epsilon}" if epsilon is not None else ""
        self.agvs: list[AdvancedMockAGV] = []
        self.metrics = MetricsCollector(
            output_dir="results", scenario_name=f"{self.name}{suffix}"
        )

    def run(self) -> dict:
        """Execute the full simulation. Returns exported file paths."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"  SCENARIO: {self.name}")
        logger.info(f"  {self.scenario['description']}")
        logger.info(f"  Fleet: {len(self.fleet_config)} AGVs | Tasks: {len(self.tasks)}")
        if self.epsilon is not None:
            logger.info(f"  Epsilon (ε): {self.epsilon}")
        logger.info(f"{'=' * 60}\n")

        try:
            self._start_fleet()
            self._wait_for_fleet_ready()
            self.metrics.start_simulation_timer()
            self.metrics.start_mqtt_monitor(list(self.fleet_config.keys()))
            self._dispatch_tasks()
            self._wait_for_completion()
            self.metrics.stop_simulation_timer()
        except KeyboardInterrupt:
            logger.warning("Simulation interrupted by user")
            self.metrics.stop_simulation_timer()
        finally:
            self._stop_fleet()
            self.metrics.stop_mqtt_monitor()

        self.metrics.print_summary()
        files = self.metrics.export_all()
        return files

    # ==================== Fleet Management ====================

    def _start_fleet(self):
        """Initialize and start all mock AGVs."""
        logger.info(f"Starting {len(self.fleet_config)} AGVs...")

        for serial, config in self.fleet_config.items():
            agv = AdvancedMockAGV(
                serial_number=serial,
                initial_node=config["node"],
                initial_battery=config["battery"],
                on_order_complete=self.metrics.record_order_complete,
            )
            agv.start()
            self.agvs.append(agv)
            time.sleep(0.3)  # Stagger connections

        logger.info(f"All {len(self.agvs)} AGVs started")

    def _wait_for_fleet_ready(self):
        """Wait for AGVs to be registered on the server."""
        logger.info("Waiting for AGVs to register with server...")
        time.sleep(3)  # Allow state messages to propagate

        for _ in range(10):
            try:
                resp = requests.get(f"{API_BASE_URL}/agvs/", timeout=5)
                if resp.status_code == 200:
                    registered = resp.json()
                    online = [
                        a for a in registered
                        if a.get("is_online") and a.get("serial_number") in self.fleet_config
                    ]
                    if len(online) >= len(self.fleet_config):
                        logger.info(f"All {len(online)} AGVs registered and online")
                        return
                    logger.info(f"  {len(online)}/{len(self.fleet_config)} AGVs online...")
            except requests.RequestException as e:
                logger.warning(f"Server not reachable: {e}")
            time.sleep(2)

        logger.warning("Not all AGVs registered, proceeding anyway...")

    def _stop_fleet(self):
        """Stop all AGVs."""
        for agv in self.agvs:
            agv.stop()
        logger.info("All AGVs stopped")

    # ==================== Task Dispatch ====================

    def _dispatch_tasks(self):
        """Send tasks to server according to scenario timing."""
        logger.info(f"\nDispatching {len(self.tasks)} tasks...")

        start_time = time.time()

        for i, task in enumerate(self.tasks):
            # Wait until the scheduled delay
            elapsed = time.time() - start_time
            wait = task["delay_s"] - elapsed
            if wait > 0:
                time.sleep(wait)

            pickup = task["pickup_node_id"]
            delivery = task["delivery_node_id"]

            logger.info(f"  Task {i + 1}/{len(self.tasks)}: {pickup} -> {delivery}")

            try:
                t_bid_start = time.time()
                payload = {
                    "pickup_node_id": pickup,
                    "delivery_node_id": delivery,
                }
                if self.epsilon is not None:
                    payload["epsilon"] = self.epsilon

                resp = requests.post(
                    f"{API_BASE_URL}/tasks/",
                    json=payload,
                    timeout=10,
                )
                bidding_time_ms = round((time.time() - t_bid_start) * 1000, 2)

                if resp.status_code == 201:
                    data = resp.json()
                    winner = data.get("winner_agv", "?")
                    order_id = data.get("order_id", "?")
                    logger.info(f"    -> Assigned to {winner} (Order: {order_id}, Bid: {bidding_time_ms}ms)")

                    self.metrics.record_task_assignment(
                        {
                            "order_id": order_id,
                            "winner_agv": winner,
                            "pickup_node": pickup,
                            "delivery_node": delivery,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "bidding_time_ms": bidding_time_ms,
                        }
                    )
                else:
                    error = resp.json().get("error", resp.text)
                    logger.error(f"    -> Failed: {error}")

            except requests.RequestException as e:
                logger.error(f"    -> API error: {e}")

        logger.info(f"All {len(self.tasks)} tasks dispatched")

    # ==================== Completion Detection ====================

    def _wait_for_completion(self):
        """Wait until all tasks are complete or timeout."""
        logger.info(f"\nWaiting for tasks to complete (timeout: {self.timeout}s)...")

        start = time.time()
        expected_tasks = len(self.tasks)
        last_status_print = 0

        while time.time() - start < self.timeout:
            completed = len(self.metrics.order_records)

            # Print status periodically
            now = time.time()
            if now - last_status_print >= STATUS_PRINT_INTERVAL:
                self._print_fleet_status(completed, expected_tasks)
                last_status_print = now

            # Check if all tasks done
            if completed >= expected_tasks:
                logger.info(f"\nAll {completed} tasks completed!")
                time.sleep(2)  # Grace period for final state messages
                return

            time.sleep(1)

        elapsed = time.time() - start
        completed = len(self.metrics.order_records)
        logger.warning(
            f"\nTimeout after {elapsed:.0f}s. "
            f"Completed: {completed}/{expected_tasks}"
        )

    def _print_fleet_status(self, completed: int, total: int):
        """Print current fleet status."""
        elapsed = time.time() - self.metrics._simulation_start
        print(f"\n--- Status @ {elapsed:.0f}s | Tasks: {completed}/{total} ---")
        print(f"  {'AGV':<10} {'State':<22} {'Node':<10} {'Battery':>8} {'Order':<18}")
        print(f"  {'─' * 70}")
        for agv in self.agvs:
            s = agv.status_summary
            print(
                f"  {s['serial']:<10} {s['state']:<22} {s['node']:<10} "
                f"{s['battery']:>7.1f}% {s['order']:<18}"
            )
        print()


# ==================== Main Entry Point ====================

def main():
    parser = argparse.ArgumentParser(
        description="AGV Simulation Runner - VDA5050 Compliant"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="basic",
        help=f"Scenario to run: {', '.join(list_scenarios())} or 'all'",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available scenarios"
    )
    parser.add_argument(
        "--agvs", type=int, default=0,
        help="Override fleet size (only works with basic scenario)",
    )
    parser.add_argument(
        "--api", type=str, default=None,
        help="Override API base URL (e.g., http://localhost:8000/api)",
    )
    parser.add_argument(
        "--epsilon", type=float, default=None,
        help="Hybrid objective parameter (0=MiniMax, 1=MiniSum). Sent per-request to server.",
    )

    args = parser.parse_args()

    # List scenarios
    if args.list:
        print("\nAvailable Scenarios:")
        print(f"{'─' * 60}")
        for name, sc in ALL_SCENARIOS.items():
            fleet_size = len(sc["fleet"])
            task_count = len(sc["tasks"])
            print(f"  {name:<15} {fleet_size} AGVs, {task_count} tasks")
            print(f"  {'':15} {sc['description']}\n")
        return

    # Override API URL
    if args.api:
        import config_sim
        config_sim.API_BASE_URL = args.api

    # Run scenarios
    if args.scenario == "all":
        scenarios_to_run = list(ALL_SCENARIOS.keys())
    else:
        scenarios_to_run = [args.scenario]

    all_results = {}

    for scenario_name in scenarios_to_run:
        scenario = get_scenario(scenario_name)

        # Override fleet size if specified
        if args.agvs > 0 and scenario_name == "basic":
            scenario = dict(scenario)
            scenario["fleet"] = generate_fleet(args.agvs)
            scenario["name"] = f"basic_{args.agvs}agvs"

        runner = SimulationRunner(scenario, epsilon=args.epsilon)
        files = runner.run()
        all_results[scenario_name] = files

        if len(scenarios_to_run) > 1:
            logger.info("Cooldown between scenarios...")
            time.sleep(5)

    # Final summary
    print(f"\n{'=' * 60}")
    print("  ALL SIMULATIONS COMPLETE")
    print(f"{'=' * 60}")
    for name, files in all_results.items():
        print(f"\n  {name}:")
        for metric, path in files.items():
            print(f"    {metric:<20} -> {path}")
    print()


if __name__ == "__main__":
    main()

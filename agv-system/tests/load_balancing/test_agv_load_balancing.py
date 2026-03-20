"""
Script test hệ thống AGV với nhiều xe và tasks.
Đo lường:
- Tổng thời gian hoàn thành
- Cân bằng tải giữa các AGV
"""

import requests
import time
from datetime import datetime
from collections import defaultdict
import statistics

# ==================== CONFIGURATION ====================
API_BASE_URL = "http://localhost:8000/api"
NUM_AGVS = 7  # Số lượng AGV test
NUM_TASKS = 10  # Số lượng tasks
TASK_INTERVAL = 5  # Giây giữa mỗi task (5s = gửi từ từ)

# Các node có sẵn trong hệ thống
AVAILABLE_NODES = [
    "Node_A",
    "Node_B",
    "Node_C",
    "Node_D",
    "Node_E",
    "Node_F",
    "Node_G",
    "Node_H",
]

# Tasks mẫu: (pickup, delivery)
SAMPLE_TASKS = [
    ("Node_A", "Node_C"),
    ("Node_B", "Node_D"),
    ("Node_A", "Node_E"),
    ("Node_C", "Node_F"),
    ("Node_B", "Node_G"),
    ("Node_D", "Node_H"),
    ("Node_E", "Node_A"),
    ("Node_F", "Node_B"),
    ("Node_G", "Node_C"),
    ("Node_H", "Node_D"),
]


class AGVTestRunner:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.tasks_created = []
        self.agv_task_count = defaultdict(int)  # Đếm số task mỗi AGV
        self.agv_total_distance = defaultdict(float)  # Tổng khoảng cách mỗi AGV

    def setup_agvs(self):
        """Setup AGVs với các trạng thái khác nhau"""
        print("\n" + "=" * 60)
        print("📋 SETTING UP AGVs")
        print("=" * 60)

        agvs_config = []
        for i in range(1, NUM_AGVS + 1):
            agv_data = {
                "serial_number": f"AGV_{i:02d}",
                "manufacturer": "TestManufacturer",
                "model": f"Model_v{i}",
                "is_online": True,
                # Đa dạng vị trí xuất phát và battery
                "battery_percent": 100 - (i * 5),  # 95%, 90%, 85%...
                "current_node": AVAILABLE_NODES[i % len(AVAILABLE_NODES)],
            }
            agvs_config.append(agv_data)

        # Hiển thị config
        for agv in agvs_config:
            print(
                f"  🤖 {agv['serial_number']}: "
                f"Node={agv['current_node']}, "
                f"Battery={agv['battery_percent']}%"
            )

        return agvs_config

    def create_agv_state(self, serial_number, node_id, battery):
        """Tạo state cho AGV qua API hoặc database"""
        # Note: Bạn cần có endpoint để tạo/update AGV state
        # Hoặc dùng Django shell/management command
        print(f"  ✓ Created state for {serial_number}")

    def send_task(self, pickup_node, delivery_node, task_num):
        """Gửi một transport task và log bid details"""
        url = f"{API_BASE_URL}/tasks/"
        payload = {"pickup_node_id": pickup_node, "delivery_node_id": delivery_node}

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 201:
                data = response.json()
                winner_agv = data.get("winner_agv")
                order_id = data.get("order_id")
                path = data.get("path", [])

                print(f"\n  ✅ Task #{task_num}: {pickup_node}→{delivery_node}")
                print(f"     Winner: {winner_agv} (Order: {order_id})")
                print(f"     Path: {' → '.join(path)} ({len(path) - 1} edges)")

                # Tracking
                self.tasks_created.append(
                    {
                        "task_num": task_num,
                        "pickup": pickup_node,
                        "delivery": delivery_node,
                        "winner_agv": winner_agv,
                        "order_id": order_id,
                        "path": path,
                        "timestamp": datetime.now(),
                        "path_length": len(path) - 1,
                    }
                )

                self.agv_task_count[winner_agv] += 1
                self.agv_total_distance[winner_agv] += len(path) - 1  # Edges count

                return True
            else:
                print(f"  ❌ Task #{task_num}: Failed - {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"     Error: {error_data.get('error', 'Unknown')}")
                except:
                    print(f"     Response: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"  ❌ Task #{task_num}: Error - {str(e)}")
            return False

    def generate_and_send_tasks(self):
        """Tạo và gửi tasks từ từ"""
        print("\n" + "=" * 60)
        print(f"🚀 SENDING {NUM_TASKS} TASKS (Interval: {TASK_INTERVAL}s)")
        print("=" * 60)

        success_count = 0

        for i in range(NUM_TASKS):
            # Lấy task từ danh sách mẫu (lặp lại nếu cần)
            pickup, delivery = SAMPLE_TASKS[i % len(SAMPLE_TASKS)]

            print(
                f"\n⏱️  Task #{i + 1}/{NUM_TASKS} (Waiting {TASK_INTERVAL}s before next...)"
            )

            if self.send_task(pickup, delivery, i + 1):
                success_count += 1

            # Delay giữa các tasks để AGVs có thời gian cập nhật state
            if i < NUM_TASKS - 1:  # Không delay sau task cuối
                time.sleep(TASK_INTERVAL)

        print(f"\n{'=' * 60}")
        print(f"✅ Successfully created: {success_count}/{NUM_TASKS} tasks")
        print(f"{'=' * 60}")
        return success_count

    def monitor_completion(self, timeout=300):
        """Theo dõi việc hoàn thành các orders"""
        print("\n" + "=" * 60)
        print("⏳ MONITORING ORDER COMPLETION")
        print("=" * 60)

        monitor_start = time.time()
        completed_orders = set()

        while len(completed_orders) < len(self.tasks_created):
            elapsed = time.time() - monitor_start

            if elapsed > timeout:
                print(f"\n⚠️  Timeout reached ({timeout}s)")
                break

            # Check status của từng order
            for task in self.tasks_created:
                order_id = task["order_id"]

                if order_id in completed_orders:
                    continue

                # Query order status
                try:
                    url = f"{API_BASE_URL}/orders/"
                    response = requests.get(url, timeout=5)

                    if response.status_code == 200:
                        orders = response.json()

                        for order in orders:
                            if order.get("order_id") == order_id:
                                status = order.get("status")

                                if status in ["COMPLETED", "FAILED", "CANCELLED"]:
                                    completed_orders.add(order_id)
                                    print(
                                        f"  ✓ Order {order_id}: {status} "
                                        f"(AGV: {task['winner_agv']})"
                                    )
                                    break

                except Exception as e:
                    print(f"  ⚠️  Error checking order {order_id}: {e}")

            # Progress
            progress = len(completed_orders) / len(self.tasks_created) * 100
            print(
                f"  Progress: {len(completed_orders)}/{len(self.tasks_created)} "
                f"({progress:.1f}%) - Elapsed: {elapsed:.1f}s",
                end="\r",
            )

            time.sleep(2)  # Check mỗi 2s

        return len(completed_orders)

    def calculate_load_balance_metrics(self):
        """Tính toán các metrics về cân bằng tải"""
        print("\n" + "=" * 60)
        print("📊 LOAD BALANCING METRICS")
        print("=" * 60)

        if not self.agv_task_count:
            print("No tasks assigned yet.")
            return

        # Task distribution
        print("\n📦 Task Distribution:")
        tasks_per_agv = list(self.agv_task_count.values())

        for agv, count in sorted(self.agv_task_count.items()):
            distance = self.agv_total_distance.get(agv, 0)
            bar = "█" * count
            print(f"  {agv}: {bar} {count} tasks ({distance:.0f} edges)")

        # Statistical metrics
        if len(tasks_per_agv) > 1:
            mean_tasks = statistics.mean(tasks_per_agv)
            stdev_tasks = statistics.stdev(tasks_per_agv)
            min_tasks = min(tasks_per_agv)
            max_tasks = max(tasks_per_agv)

            # Coefficient of Variation (CV) - lower is better
            cv = (stdev_tasks / mean_tasks) * 100 if mean_tasks > 0 else 0

            print("\n📈 Statistical Analysis:")
            print(f"  Mean tasks per AGV: {mean_tasks:.2f}")
            print(f"  Std Deviation: {stdev_tasks:.2f}")
            print(f"  Min/Max tasks: {min_tasks}/{max_tasks}")
            print(f"  Coefficient of Variation (CV): {cv:.2f}%")

            # Balance Score (0-100, higher is better)
            balance_score = max(0, 100 - (cv * 2))
            print(f"\n⚖️  Balance Score: {balance_score:.1f}/100")

            if cv < 15:
                print("  Status: ✅ Excellent load balancing")
            elif cv < 30:
                print("  Status: ✔️  Good load balancing")
            elif cv < 50:
                print("  Status: ⚠️  Fair load balancing")
            else:
                print("  Status: ❌ Poor load balancing")

        # Distance distribution
        print("\n📏 Total Distance Distribution:")
        distances = list(self.agv_total_distance.values())
        if distances:
            mean_dist = statistics.mean(distances)
            print(f"  Mean distance per AGV: {mean_dist:.2f} edges")
            print(f"  Total distance traveled: {sum(distances):.0f} edges")

    def wait_for_completion(self):
        """Đợi cho tất cả tasks hoàn thành và đánh giá thực tế"""
        print("\n" + "=" * 60)
        print("⏳ WAITING FOR ALL TASKS TO COMPLETE...")
        print("=" * 60)

        # Estimate completion time based on path lengths
        total_edges = sum(task["path_length"] for task in self.tasks_created)
        estimated_time = total_edges * 3 + 30  # 3s per edge + buffer

        print(f"\n📊 Estimated completion time: {estimated_time:.0f}s")
        print(f"   Total edges to travel: {total_edges}")
        print(f"   Tasks in progress: {len(self.tasks_created)}")

        # Wait with progress indicator
        wait_time = 0
        check_interval = 5

        while wait_time < estimated_time:
            time.sleep(check_interval)
            wait_time += check_interval
            progress = (wait_time / estimated_time) * 100
            print(
                f"   Progress: {min(progress, 100):.1f}% ({wait_time}s / {estimated_time:.0f}s)",
                end="\r",
            )

        print("\n\n✅ Estimated time elapsed. Fetching final results...")

    def evaluate_actual_results(self):
        """Đánh giá kết quả thực tế từ database"""
        print("\n" + "=" * 60)
        print("📈 ACTUAL RESULTS EVALUATION")
        print("=" * 60)

        try:
            # Get all orders
            url = f"{API_BASE_URL}/orders/"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                print("⚠️  Cannot fetch orders from server")
                return

            orders = response.json()

            # Analyze orders
            completed_orders = [o for o in orders if o.get("status") == "COMPLETED"]
            active_orders = [o for o in orders if o.get("status") in ["SENT", "ACTIVE"]]
            queued_orders = [o for o in orders if o.get("status") == "QUEUED"]

            print("\n📦 Order Status:")
            print(f"   Completed: {len(completed_orders)}")
            print(f"   Active: {len(active_orders)}")
            print(f"   Queued: {len(queued_orders)}")
            print(f"   Total: {len(orders)}")

            # Get actual AGV distribution
            actual_agv_distribution = defaultdict(int)

            # Build AGV ID to serial mapping
            agv_id_to_serial = {}
            try:
                agvs_response = requests.get(f"{API_BASE_URL}/agvs/", timeout=5)
                if agvs_response.status_code == 200:
                    agvs_list = agvs_response.json()
                    for agv in agvs_list:
                        agv_id_to_serial[agv["id"]] = agv["serial_number"]
            except:
                pass

            for order in orders:
                # AGV is returned as ID (integer)
                agv_id = order.get("agv")
                if agv_id:
                    agv_serial = agv_id_to_serial.get(agv_id, f"AGV_ID_{agv_id}")
                    actual_agv_distribution[agv_serial] += 1

            print("\n🤖 Actual AGV Task Distribution:")
            for agv, count in sorted(actual_agv_distribution.items()):
                bar = "█" * count
                status = "✅" if count > 0 else "⚠️ "
                print(f"   {status} {agv}: {bar} {count} orders")

            # Compare with expected
            print("\n📊 Comparison (Expected vs Actual):")
            all_agvs = set(
                list(self.agv_task_count.keys()) + list(actual_agv_distribution.keys())
            )

            for agv in sorted(all_agvs):
                expected = self.agv_task_count.get(agv, 0)
                actual = actual_agv_distribution.get(agv, 0)
                match = "✅" if expected == actual else "⚠️ "
                print(f"   {match} {agv}: Expected {expected}, Actual {actual}")

            # Get AGV states for battery analysis
            print("\n🔋 Final Battery Levels:")
            for i in range(1, NUM_AGVS + 1):
                agv_serial = f"AGV_{i:02d}"
                try:
                    url = f"{API_BASE_URL}/agvs/{agv_serial}/"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        agv_data = response.json()
                        # Get latest state
                        states_url = f"{API_BASE_URL}/agvs/{agv_serial}/states/"
                        states_response = requests.get(states_url, timeout=5)
                        if states_response.status_code == 200:
                            states = states_response.json()
                            if states:
                                latest_state = states[0]
                                battery = latest_state.get("battery_state", {}).get(
                                    "batteryCharge", 0
                                )
                                tasks = actual_agv_distribution.get(agv_serial, 0)
                                battery_icon = (
                                    "🔋"
                                    if battery > 50
                                    else "🪫"
                                    if battery > 20
                                    else "⚠️ "
                                )
                                print(
                                    f"   {battery_icon} {agv_serial}: {battery:.1f}% ({tasks} tasks)"
                                )
                except:
                    pass

        except Exception as e:
            print(f"❌ Error evaluating results: {e}")

    def generate_report(self):
        """Tạo báo cáo tổng kết"""
        print("\n" + "=" * 60)
        print("📋 FINAL REPORT")
        print("=" * 60)

        if self.start_time and self.end_time:
            total_time = self.end_time - self.start_time
            print(f"\n⏱️  Total Execution Time: {total_time:.2f} seconds")
            print(
                f"   Start: {datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S')}"
            )
            print(
                f"   End: {datetime.fromtimestamp(self.end_time).strftime('%H:%M:%S')}"
            )

        print("\n📦 Task Summary:")
        print(f"   Total tasks created: {len(self.tasks_created)}")

        print("\n🤖 AGV Summary:")
        print(f"   Total AGVs: {NUM_AGVS}")
        print(f"   Active AGVs: {len(self.agv_task_count)}")

        # Throughput
        if self.start_time and self.end_time:
            total_time = self.end_time - self.start_time
            if total_time > 0:
                throughput = len(self.tasks_created) / total_time
                print("\n📊 Performance:")
                print(f"   Throughput: {throughput:.2f} tasks/second")
                print(
                    f"   Avg time per task: {total_time / len(self.tasks_created):.2f} seconds"
                )

    def run(self):
        """Chạy toàn bộ test scenario"""
        print("\n" + "=" * 60)
        print("🧪 AGV LOAD BALANCING TEST")
        print("=" * 60)
        print("Configuration:")
        print(f"  - Number of AGVs: {NUM_AGVS}")
        print(f"  - Number of Tasks: {NUM_TASKS}")
        print(f"  - Task Interval: {TASK_INTERVAL}s")
        print(f"  - API Endpoint: {API_BASE_URL}")

        # Step 1: Setup AGVs
        agvs = self.setup_agvs()

        # Step 2: Send tasks (từ từ)
        self.start_time = time.time()
        success_count = self.generate_and_send_tasks()

        if success_count == 0:
            print("\n❌ No tasks were created successfully. Exiting.")
            return

        # Step 3: Calculate immediate metrics (dựa trên bidding)
        print("\n" + "=" * 60)
        print("📊 IMMEDIATE METRICS (Based on Bidding)")
        print("=" * 60)
        self.calculate_load_balance_metrics()

        # Step 4: Wait briefly and evaluate actual progress
        print("\n" + "=" * 60)
        print("⏳ CHECKING ACTUAL RESULTS (After 20s)")
        print("=" * 60)
        print("\n⏱️  Waiting 20s to check progress...")
        time.sleep(20)

        # Step 5: Evaluate actual results from database
        self.evaluate_actual_results()

        # Step 6: Final timing
        self.end_time = time.time()

        # Step 7: Generate final report
        print("\n" + "=" * 60)
        print("✅ TEST COMPLETED")
        print("=" * 60)
        self.generate_report()


if __name__ == "__main__":
    runner = AGVTestRunner()
    runner.run()

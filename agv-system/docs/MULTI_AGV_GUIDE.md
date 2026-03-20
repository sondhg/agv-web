# Multi-AGV Simulator & Testing Guide

## 📁 Cấu trúc thư mục

```
agv_project/
├── tests/
│   ├── README.md                    # Tổng quan testing
│   ├── simulators/
│   │   ├── mock_agv.py             # Single AGV simulator
│   │   └── multi_mock_agv.py       # Multi-AGV simulator
│   └── load_balancing/
│       └── test_agv_load_balancing.py  # Load balancing test suite
├── docs/
│   ├── MULTI_AGV_GUIDE.md          # Hướng dẫn này
│   └── BIDDING_SYSTEM.md           # Chi tiết về bidding system
└── backend/
    └── vda5050/
        └── modules/
            └── bidding/            # Bidding engine & calculators
```

## 🚀 Quick Start

### Bước 1: Khởi động môi trường
```powershell
# Khởi động Docker containers
docker-compose up -d

# Kiểm tra trạng thái
docker-compose ps
```

### Bước 2: Setup AGVs và Graph
```powershell
# Tạo 7 AGVs test với battery khác nhau
docker-compose exec web python manage.py setup_test_agvs --count 7

# Tạo graph topology (8 nodes, grid 2x4)
docker-compose exec web python manage.py setup_test_graph
```

### Bước 3: Chạy Multi-AGV Simulator
```powershell
cd tests/simulators
python multi_mock_agv.py
```

### Bước 4: Chạy Load Balancing Test
```powershell
# Mở terminal khác
cd tests/load_balancing
python test_agv_load_balancing.py
```

## 🧪 Testing Workflow

### 1. Multi-AGV Simulator (`tests/simulators/multi_mock_agv.py`)

**Mục đích**: Mô phỏng nhiều AGVs hoạt động đồng thời, nhận và thực hiện orders.

**Tính năng**:
- ✅ Mô phỏng 7 AGVs với battery drain theo trạng thái (IDLE/MOVING/LOADED)
- ✅ Kết nối MQTT, subscribe topics: order, instantActions, connection
- ✅ Publish state updates mỗi 2 giây
- ✅ Xử lý orders: di chuyển qua nodes, cập nhật trạng thái
- ✅ Thread riêng cho mỗi AGV

**Output**:
```
🤖 AGV_01: Connected to broker
📦 AGV_01: Order received: ORD_ABC123
🚚 AGV_01: Moving Node_A → Node_B (Battery: 94.5%)
✅ AGV_01: Completed order ORD_ABC123

📊 Fleet Status (30s interval):
   AGV_01: Node_B | Battery: 93.2% | Status: IDLE | Orders: 3
   AGV_02: Node_C | Battery: 88.1% | Status: MOVING | Orders: 2
```

### 2. Load Balancing Test (`tests/load_balancing/test_agv_load_balancing.py`)

**Mục đích**: Đo lường hiệu quả phân bổ công việc và cân bằng tải giữa các AGVs.

**Cấu hình**:
```python
NUM_AGVS = 7          # Số lượng AGVs
NUM_TASKS = 10        # Số tasks test
TASK_INTERVAL = 5     # Giây giữa mỗi task (gửi từ từ)
```

**Quy trình test**:
1. **Setup**: Tạo/reset 7 AGVs với battery 95%, 90%, 85%, 80%, 75%, 70%, 65%
2. **Send Tasks**: Gửi 10 tasks với interval 5s (tổng ~50s)
3. **Immediate Metrics**: Tính CV, Balance Score từ kết quả bidding
4. **Wait**: Đợi 20s cho tasks execute
5. **Actual Metrics**: Query database, so sánh Expected vs Actual

**Metrics đo lường**:
- **Coefficient of Variation (CV)**: Độ biến thiên task distribution
  - 0% = Perfect balance
  - <30% = Excellent
  - 30-50% = Good/Fair
  - >50% = Poor
  
- **Balance Score**: 0-100, tính từ CV và task spread
  - 100 = Perfect (CV=0)
  - 70-100 = Excellent
  - 50-70 = Good
  - 30-50 = Fair
  - <30 = Poor

**Output mẫu**:
```
📦 Task Distribution:
  AGV_01: ███ 3 tasks (5 edges)
  AGV_02: ██ 2 tasks (4 edges)
  AGV_04: █ 1 tasks (2 edges)
  AGV_05: ██ 2 tasks (4 edges)
  AGV_06: ██ 2 tasks (5 edges)

📈 Statistical Analysis:
  Mean tasks per AGV: 2.00
  Std Deviation: 0.71
  Coefficient of Variation (CV): 35.36%

⚖️  Balance Score: 29.3/100
  Status: ⚠️  Fair load balancing

📊 Comparison (Expected vs Actual):
   ✅ AGV_01: Expected 3, Actual 3
   ✅ AGV_05: Expected 2, Actual 2
   ⚠️  AGV_04: Expected 1, Actual 2
```

## 🔍 Chi tiết hoạt động

### Battery Drain Simulation
```python
IDLE_DRAIN_RATE = 0.05      # %/second (đứng yên)
MOVING_DRAIN_RATE = 0.15    # %/second (di chuyển không tải)
MOVING_WITH_LOAD_DRAIN_RATE = 0.25  # %/second (di chuyển có tải)
```

**Ví dụ**: AGV di chuyển 10 edges (10s) với tải:
- Battery drain = 10s × 0.25%/s = 2.5%
- 95% → 92.5%

### Order Execution Flow
1. **Receive Order**: MQTT topic `uagv/v2/{mfr}/{serial}/order`
2. **Parse Nodes**: Extract pickup_node, delivery_node
3. **Execute Leg 1**: Current → Pickup (empty, MOVING drain)
4. **Execute Leg 2**: Pickup → Delivery (loaded, MOVING_WITH_LOAD drain)
5. **Publish State**: Every 2s with battery, position, status
6. **Complete**: Status = FINISHED

### MQTT Topics
```
# Inbound (server → AGV)
uagv/v2/{manufacturer}/{serial}/order           # Orders
uagv/v2/{manufacturer}/{serial}/instantActions  # Instant actions
uagv/v2/{manufacturer}/{serial}/connection      # Connection commands

# Outbound (AGV → server)
uagv/v2/{manufacturer}/{serial}/state           # State updates
uagv/v2/{manufacturer}/{serial}/visualization   # Visualization
```

## 📊 Kết quả thực tế

### Test Run: 10 Tasks, 7 AGVs

**Configuration**:
- AGVs: 7 (positions: B,C,D,E,F,G,H | battery: 95%,90%,85%,80%,75%,70%,65%)
- Tasks: 10 (sent gradually, 5s interval)
- Total time: ~66 seconds

**Results**:
```
✅ Task Distribution: 5/7 AGVs received tasks
   - AGV_01: 3 tasks (45% workload)
   - AGV_02, AGV_05, AGV_06: 2 tasks each
   - AGV_04: 1 task
   - AGV_03, AGV_07: 0 tasks

📈 Metrics:
   - CV: 35.36% (Fair balance)
   - Balance Score: 29.3/100
   - Throughput: 0.15 tasks/s
   - Completion: 100% (10/10 orders)

🔋 Battery Impact:
   - Max drain: AGV_01 (95% → 81.8%, -13.2%)
   - Avg drain per active AGV: ~8-10%
```

**Observations**:
- ✅ Bidding system considers active tasks (wait cost)
- ✅ Tasks sent gradually allow AGVs to update bids
- ✅ AGVs closer to pickup points preferred
- ⚠️  Some AGVs idle (far from action or low battery)

## 🛠️ Troubleshooting

### AGVs không nhận orders
```powershell
# Kiểm tra MQTT broker
docker-compose logs mosquitto

# Kiểm tra web service logs
docker-compose logs web

# Verify AGVs online
curl http://localhost:8000/api/agvs/
```

### Load balancing kém
- **Tăng số tasks**: NUM_TASKS = 20
- **Kiểm tra graph topology**: Ensure all nodes connected
- **Reset AGV states**: `setup_test_agvs --count 7` (fresh start)

### Performance thấp
- **Giảm TASK_INTERVAL**: 3-5s cho realtime
- **Tăng số AGVs**: Spread workload
- **Optimize paths**: Check graph_engine pathfinding

## 📚 Tài liệu liên quan

- [BIDDING_SYSTEM.md](./BIDDING_SYSTEM.md) - Chi tiết về bidding algorithm
- [tests/README.md](../tests/README.md) - Testing framework overview
- [VDA5050 Spec](https://github.com/VDA5050/VDA5050) - Protocol specification

## 🎯 Next Steps

1. **Scale Testing**: Test với 20-50 AGVs
2. **Complex Graphs**: Non-grid topologies
3. **Dynamic Obstacles**: Simulate blocked paths
4. **Battery Management**: Charging station integration
5. **Multi-objective**: Balance time + energy + utilization

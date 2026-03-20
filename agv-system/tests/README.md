# AGV Testing Framework

## 📚 Tổng quan

Testing framework cung cấp công cụ để test và đánh giá hiệu suất của AGV Fleet Management System, bao gồm:
- **Simulators**: Mô phỏng AGVs hoạt động
- **Load Balancing Tests**: Đánh giá phân bổ công việc
- **Integration Tests**: Test end-to-end workflow

## 📁 Cấu trúc

```
tests/
├── README.md                      # File này
├── TEST_README.md                 # Legacy test docs
├── simulators/
│   ├── mock_agv.py               # Single AGV simulator
│   └── multi_mock_agv.py         # Multi-AGV fleet simulator
└── load_balancing/
    └── test_agv_load_balancing.py  # Load balancing test suite
```

## 🧪 Test Suites

### 1. Simulators

#### `simulators/mock_agv.py`
**Mục đích**: Mô phỏng 1 AGV đơn lẻ với VDA5050 protocol.

**Tính năng**:
- MQTT communication (subscribe/publish)
- State updates với battery drain
- Order execution
- Manual testing tool

**Sử dụng**:
```powershell
cd tests/simulators
python mock_agv.py
```

#### `simulators/multi_mock_agv.py`
**Mục đích**: Mô phỏng fleet với nhiều AGVs hoạt động đồng thời.

**Tính năng**:
- 7 AGVs với threads riêng biệt
- Battery drain simulation (IDLE/MOVING/LOADED)
- Concurrent order execution
- Fleet status monitoring

**Sử dụng**:
```powershell
cd tests/simulators
python multi_mock_agv.py
```

**Output**:
```
🤖 Initialized AGV_01 at Node_B (Battery: 95%)
✅ AGV_01: Connected to broker
📦 AGV_01: Order received: ORD_ABC
🚚 AGV_01: Moving Node_A → Node_B (Battery: 94.5%)

📊 Fleet Status (every 30s):
   AGV_01: Node_B | Battery: 93.2% | Orders: 3
   AGV_02: Node_C | Battery: 88.1% | Orders: 2
```

### 2. Load Balancing Tests

#### `load_balancing/test_agv_load_balancing.py`
**Mục đích**: Đánh giá hiệu quả phân bổ công việc của bidding system.

**Metrics**:
- Task distribution across AGVs
- Coefficient of Variation (CV)
- Balance Score (0-100)
- Battery consumption
- Throughput

**Cấu hình**:
```python
NUM_AGVS = 7          # Số AGVs test
NUM_TASKS = 10        # Số tasks
TASK_INTERVAL = 5     # Giây giữa mỗi task
```

**Sử dụng**:
```powershell
cd tests/load_balancing
python test_agv_load_balancing.py
```

**Output mẫu**:
```
📦 Task Distribution:
  AGV_01: ███ 3 tasks (5 edges)
  AGV_02: ██ 2 tasks (4 edges)
  AGV_04: █ 1 tasks (2 edges)

📈 Statistical Analysis:
  Coefficient of Variation (CV): 35.36%
  Balance Score: 29.3/100 (⚠️  Fair)

📊 Comparison (Expected vs Actual):
   ✅ AGV_01: Expected 3, Actual 3
   ✅ AGV_05: Expected 2, Actual 2

🔋 Final Battery Levels:
   🔋 AGV_01: 81.8% (-13.2%)
   🔋 AGV_02: 87.0% (-3.0%)
```

## 🔧 Setup Requirements

### Prerequisites
```powershell
# 1. Docker containers running
docker-compose up -d

# 2. Database migrated
docker-compose exec web python manage.py migrate

# 3. Test data setup
docker-compose exec web python manage.py setup_test_agvs --count 7
docker-compose exec web python manage.py setup_test_graph
```

### Python Dependencies
```
paho-mqtt==1.6.1
requests==2.31.0
```

## 📊 Test Scenarios

### Scenario 1: Basic Fleet Operation
**Objective**: Verify AGVs can receive and execute orders.

**Steps**:
1. Start `multi_mock_agv.py`
2. Send 3 orders via API
3. Verify orders completed
4. Check battery drain

**Expected**:
- All orders completed
- Battery drain ~2-5% per order
- No errors in logs

### Scenario 2: Load Balancing
**Objective**: Measure task distribution fairness.

**Steps**:
1. Start `multi_mock_agv.py`
2. Run `test_agv_load_balancing.py`
3. Analyze CV and Balance Score

**Expected**:
- CV < 50% (Good/Fair balance)
- 5-7 AGVs active (out of 7)
- Battery distributed evenly

### Scenario 3: Active Task Consideration
**Objective**: Verify bidding considers busy AGVs.

**Steps**:
1. Send order to AGV_01 (long distance)
2. Immediately send another order
3. Check if AGV_02 wins (idle)

**Expected**:
- AGV_01 has higher wait_time
- AGV_02 wins second auction
- Log shows wait_cost calculation

### Scenario 4: Scale Test
**Objective**: Test with high load.

**Steps**:
1. Set NUM_TASKS = 20
2. Set TASK_INTERVAL = 3
3. Run test
4. Monitor completion time

**Expected**:
- All 20 tasks completed
- CV < 50%
- No timeout errors
- Throughput ~0.2-0.3 tasks/s

## 📈 Performance Benchmarks

### Target Metrics

| Metric | Excellent | Good | Fair | Poor |
|--------|-----------|------|------|------|
| CV | <30% | 30-40% | 40-50% | >50% |
| Balance Score | >70 | 50-70 | 30-50 | <30 |
| Throughput | >0.25 | 0.15-0.25 | 0.10-0.15 | <0.10 |
| Completion Rate | 100% | >95% | >90% | <90% |

### Actual Results (10 tasks, 7 AGVs)

```
✅ CV: 35.36% (Fair)
⚠️  Balance Score: 29.3/100 (Fair)
✅ Throughput: 0.15 tasks/s (Good)
✅ Completion: 100%
```

## 🐛 Debugging

### AGV không nhận orders
```powershell
# Check MQTT broker
docker-compose logs mosquitto | Select-String "AGV"

# Check AGV states
curl http://localhost:8000/api/agvs/AGV_01/
```

### Load balancing kém
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test fails
```powershell
# Reset environment
docker-compose down
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py setup_test_agvs --count 7
docker-compose exec web python manage.py setup_test_graph
```

## 📝 Writing New Tests

### Template
```python
import requests
import time

API_BASE = "http://localhost:8000/api"

def test_my_scenario():
    # Setup
    agvs = setup_agvs()
    
    # Execute
    response = requests.post(
        f"{API_BASE}/tasks/",
        json={
            "pickup_node_id": "Node_A",
            "delivery_node_id": "Node_C"
        }
    )
    
    # Verify
    assert response.status_code == 201
    order_id = response.json()['order_id']
    
    # Cleanup
    time.sleep(5)
    order = requests.get(f"{API_BASE}/orders/{order_id}/")
    assert order.json()['status'] == 'COMPLETED'

if __name__ == "__main__":
    test_my_scenario()
```

## 🎯 Future Enhancements

### Short-term
- [ ] Automated test runner (pytest)
- [ ] CI/CD integration
- [ ] Performance regression tests
- [ ] Coverage reports

### Long-term
- [ ] Stress tests (50+ AGVs)
- [ ] Failure scenario tests (AGV disconnect, path blocked)
- [ ] Multi-warehouse topologies
- [ ] Battery charging simulation
- [ ] Dynamic task priorities

## 📚 Related Documentation

- [MULTI_AGV_GUIDE.md](../docs/MULTI_AGV_GUIDE.md) - Multi-AGV simulator guide
- [BIDDING_SYSTEM.md](../docs/BIDDING_SYSTEM.md) - Bidding algorithm details
- [VDA5050 Protocol](https://github.com/VDA5050/VDA5050) - Standard reference

## 🤝 Contributing

When adding new tests:
1. Follow existing file structure
2. Document metrics and expected results
3. Add to this README
4. Include example output
5. Test in clean environment

## 📞 Support

For issues:
1. Check logs: `docker-compose logs web`
2. Verify setup: `setup_test_agvs`, `setup_test_graph`
3. Review docs: MULTI_AGV_GUIDE.md, BIDDING_SYSTEM.md

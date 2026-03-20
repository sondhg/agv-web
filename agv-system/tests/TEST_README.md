# AGV Load Balancing Test Suite

## 📋 Tổng quan
Script test hệ thống AGV với nhiều xe và tasks để đánh giá:
- **Tổng thời gian hoàn thành** các tasks
- **Cân bằng tải** giữa các AGV
- **Hiệu suất** của bidding engine

## 🚀 Hướng dẫn sử dụng

### Bước 1: Setup Test AGVs

Tạo AGVs với các trạng thái khác nhau trong database:

```bash
# Trong Docker container hoặc local
docker-compose exec web python manage.py setup_test_agvs --count 7

# Hoặc nếu chạy local
cd backend
python manage.py setup_test_agvs --count 10
```

**Output mong đợi:**
```
============================================================
🤖 Setting up 7 test AGVs
============================================================
  ✅ Created AGV_01: Node=Node_A, Battery=95%
  ✅ Created AGV_02: Node=Node_B, Battery=90%
  ✅ Created AGV_03: Node=Node_C, Battery=85%
  ...
============================================================
✅ Successfully setup 7 AGVs
============================================================
```

### Bước 2: Chạy Test Script

```bash
# Đảm bảo server đang chạy
docker-compose up -d

# Chạy test script
python test_agv_load_balancing.py
```

### Bước 3: Xem Kết quả

Script sẽ hiển thị:

#### 📊 Task Distribution
```
📦 Task Distribution:
  AGV_01: ████ 4 tasks (12 edges)
  AGV_02: ███ 3 tasks (9 edges)
  AGV_03: ███ 3 tasks (10 edges)
  ...
```

#### 📈 Statistical Analysis
```
📈 Statistical Analysis:
  Mean tasks per AGV: 2.86
  Std Deviation: 0.69
  Min/Max tasks: 2/4
  Coefficient of Variation (CV): 24.14%

⚖️  Balance Score: 51.7/100
  Status: ⚠️  Fair load balancing
```

#### ⏱️ Performance Report
```
⏱️  Total Execution Time: 12.45 seconds
   Start: 14:30:15
   End: 14:30:27

📊 Performance:
   Throughput: 1.61 tasks/second
   Avg time per task: 0.62 seconds
```

## 🔧 Cấu hình

Chỉnh sửa trong file `test_agv_load_balancing.py`:

```python
# Số lượng AGV
NUM_AGVS = 7

# Số lượng tasks
NUM_TASKS = 20

# API endpoint
API_BASE_URL = "http://localhost:8000/api"

# Các tasks mẫu (pickup, delivery)
SAMPLE_TASKS = [
    ("Node_A", "Node_C"),
    ("Node_B", "Node_D"),
    ("Node_A", "Node_E"),
    # ... thêm tasks
]
```

## 📊 Metrics Giải thích

### Load Balancing Metrics

- **Coefficient of Variation (CV)**:
  - < 15%: Excellent load balancing
  - 15-30%: Good load balancing
  - 30-50%: Fair load balancing
  - > 50%: Poor load balancing

- **Balance Score** (0-100):
  - Cao hơn = tốt hơn
  - Tính từ CV: `100 - (CV * 2)`

### Performance Metrics

- **Throughput**: Số tasks/giây
- **Success Rate**: % tasks hoàn thành thành công
- **Total Execution Time**: Tổng thời gian chạy test

## 🎯 Test Scenarios

### Scenario 1: Balanced Load (Recommended)
```python
NUM_AGVS = 7
NUM_TASKS = 20
# Expected: CV < 30%, good distribution
```

### Scenario 2: High Load
```python
NUM_AGVS = 5
NUM_TASKS = 50
# Test với nhiều tasks, ít AGVs
```

### Scenario 3: Many AGVs
```python
NUM_AGVS = 10
NUM_TASKS = 15
# Test với nhiều AGVs, ít tasks
```

## 🔍 Monitoring Real-time

Để theo dõi real-time completion (tốn thời gian hơn):

Uncomment dòng này trong `runner.run()`:
```python
# Step 4: Monitor completion
completed = self.monitor_completion(timeout=300)
self.end_time = time.time()
```

## ⚠️ Lưu ý

1. **Đảm bảo server chạy**: `docker-compose ps`
2. **Check graph nodes**: Các node phải tồn tại trong GraphEngine
3. **Database clean**: Reset data nếu cần:
   ```bash
   docker-compose exec web python manage.py flush
   ```
4. **MQTT Listener**: Đảm bảo MQTT listener đang chạy để xử lý orders

## 🐛 Troubleshooting

### Error: "No AGVs online"
```bash
# Kiểm tra AGVs trong database
docker-compose exec web python manage.py shell
>>> from vda5050.models import AGV
>>> AGV.objects.filter(is_online=True).count()
```

### Error: "No path found"
- Kiểm tra GraphNodes và GraphEdges đã được tạo
- Xem log trong backend để debug pathfinding

### Error: Connection refused
- Đảm bảo server đang chạy: `docker-compose up -d`
- Check port 8000: `curl http://localhost:8000/api/agvs/`

## 📝 Output Files (Optional)

Để lưu kết quả ra file, thêm vào script:
```python
import json

# Sau khi chạy xong
with open('test_results.json', 'w') as f:
    json.dump({
        'tasks': runner.tasks_created,
        'agv_distribution': dict(runner.agv_task_count),
        'metrics': {
            'total_time': runner.end_time - runner.start_time,
            'success_rate': completed / len(runner.tasks_created)
        }
    }, f, indent=2, default=str)
```

## 🎓 Advanced Usage

### Custom Task Patterns
```python
# Sequential tasks (stress test một path)
SAMPLE_TASKS = [("Node_A", "Node_H")] * 20

# Random tasks
import random
SAMPLE_TASKS = [
    (random.choice(AVAILABLE_NODES), random.choice(AVAILABLE_NODES))
    for _ in range(50)
]
```

### Monitor with Progress Bar
```bash
pip install tqdm
```
```python
from tqdm import tqdm

for i in tqdm(range(NUM_TASKS), desc="Sending tasks"):
    # ...
```

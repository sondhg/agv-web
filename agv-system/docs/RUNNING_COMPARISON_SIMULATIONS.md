# Hướng dẫn Chạy Mô Phỏng So Sánh 3 Phương Pháp Đấu Thầu

## 📋 Mục Lục
1. [Tổng quan](#tổng-quan)
2. [Chuẩn bị môi trường](#chuẩn-bị-môi-trường)
3. [Chạy từng phương pháp](#chạy-từng-phương-pháp)
4. [Chạy so sánh toàn diện](#chạy-so-sánh-toàn-diện)
5. [Phân tích kết quả](#phân-tích-kết-quả)
6. [Khắc phục sự cố](#khắc-phục-sự-cố)

---

## 📖 Tổng Quan

Ba phương pháp đấu thầu được cung cấp:

| Phương Pháp | Biến Môi Trường | Đặc Điểm |
|---|---|---|
| **SSI_MARGINAL** | `AUCTION_ALGORITHM=SSI_MARGINAL` | Tối ưu đa mục tiêu (energy + time + fairness) |
| **GREEDY_ETA** | `AUCTION_ALGORITHM=GREEDY_ETA` | Tối thiểu thời gian hoàn thành theo ước lượng queue đơn giản |
| **GREEDY_DISTANCE** | `AUCTION_ALGORITHM=GREEDY_DISTANCE` | Tối thiểu khoảng cách, không xét queue |

### Công Thức Đấu Thầu

**GREEDY_DISTANCE**:
```
Bid = D(N_current → N_pickup)
```
- Chỉ dùng khoảng cách từ vị trí HIỆN TẠI đến pickup
- KHÔNG xét hàng đợi, KHÔNG xét năng lượng

**GREEDY_ETA**:
```
Bid = T_queue_estimated + T_travel(N_current → N_pickup)
```
- Xét thời gian hàng đợi dự kiến
- KHÔNG xét năng lượng, KHÔNG áp dụng penalty pin yếu
- KHÔNG tính chặng pickup → delivery vào giá thầu

**SSI_MARGINAL**:
```
Bid = ε × MiniSum + (1-ε) × MiniMax
MiniSum = K_E × E_norm + K_T × T_norm
MiniMax = K_E × (E_norm + E_queue) + K_T × (T_norm + T_queue) + Conflict_Penalty + Queue_Depth_Penalty
Bid *= Battery_Penalty
```
- Xét năng lượng, thời gian, công bằng, tắc nghẽn
- Áp dụng soft penalty cho pin yếu

---

## 🔧 Chuẩn Bị Môi Trường

### 1. Khởi động Backend (Django)

```bash
cd agv-system
docker-compose up -d
```

Chờ cho đến khi Docker container chạy:
```bash
docker-compose ps
# STATUS: "Up" cho cả 3 container (web, db, mosquitto)
```

### 2. Xác Nhận Kết Nối API

```bash
# Kiểm tra server API có sẵn không
curl http://localhost:8000/api/agvs/ -s | jq . | head -20
```

### 3. Chuẩn Bị Thư Mục Kết Quả

```bash
# Tạo thư mục kết quả nếu chưa tồn tại
mkdir -p agv-system/tests/simulators/results
```

---

## 🚀 Chạy Từng Phương Pháp

### Chạy GREEDY_DISTANCE

```bash
cd agv-system/tests/simulators

# Cách 1: Chuẩn hóa với seed cố định (khuyến khích)
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"
$env:SIM_SCENARIO_SEED="42"
$env:SIM_TIME_SCALE="0.1"
python multi_agent_runner.py --scenario continuous_shift

# Cách 2: Đơn giản (seed random)
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"
python multi_agent_runner.py --scenario continuous_shift
```

**Kết quả xuất ra:**
```
results/
└── continuous_shift/
    ├── continuous_shift_XXXXXXX_fleet_summary.csv
    ├── continuous_shift_XXXXXXX_agv_summary.csv
    ├── continuous_shift_XXXXXXX_orders.csv
    └── continuous_shift_XXXXXXX_assignments.csv
```

### Chạy GREEDY_ETA

```bash
cd agv-system/tests/simulators

# Sử dụng seed tương tự để so sánh công bằng
$env:AUCTION_ALGORITHM="GREEDY_ETA"
$env:SIM_SCENARIO_SEED="42"
$env:SIM_TIME_SCALE="0.1"
python multi_agent_runner.py --scenario continuous_shift
```

### Chạy SSI_MARGINAL (Mặc Định)

```bash
cd agv-system/tests/simulators

# Với epsilon mặc định (từ constant.py, thường là 0.5)
$env:AUCTION_ALGORITHM="SSI_MARGINAL"
$env:SIM_SCENARIO_SEED="42"
$env:SIM_TIME_SCALE="0.1"
python multi_agent_runner.py --scenario continuous_shift

# Hoặc với epsilon tùy chỉnh (0 = MiniMax, 1 = MiniSum)
$env:AUCTION_ALGORITHM="SSI_MARGINAL"
$env:SIM_SCENARIO_SEED="42"
python multi_agent_runner.py --scenario continuous_shift --epsilon 0.5
```

---

## 🔬 Chạy So Sánh Toàn Diện

### Kịch Bản 1: Continuous Shift (Endurance)

Chạy liên tiếp 3 phương pháp với cùng seed:

```bash
cd agv-system/tests/simulators

# Cấu hình chung
$env:SIM_SCENARIO_SEED="42"
$env:SIM_TIME_SCALE="0.1"

# Run 1: GREEDY_DISTANCE
echo ">>> GREEDY_DISTANCE"
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"
python multi_agent_runner.py --scenario continuous_shift
Start-Sleep -Seconds 5

# Run 2: GREEDY_ETA
echo ">>> GREEDY_ETA"
$env:AUCTION_ALGORITHM="GREEDY_ETA"
python multi_agent_runner.py --scenario continuous_shift
Start-Sleep -Seconds 5

# Run 3: SSI_MARGINAL
echo ">>> SSI_MARGINAL (mặc định)"
$env:AUCTION_ALGORITHM="SSI_MARGINAL"
python multi_agent_runner.py --scenario continuous_shift
```

### Kịch Bản 2: Deadlock Contention (Stress Test)

Kiểm tra ổn định dưới tắc nghẽn:

```bash
cd agv-system/tests/simulators

$env:SIM_SCENARIO_SEED="42"

# Run 1: GREEDY_DISTANCE
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"
python multi_agent_runner.py --scenario deadlock

# Run 2: GREEDY_ETA
$env:AUCTION_ALGORITHM="GREEDY_ETA"
python multi_agent_runner.py --scenario deadlock

# Run 3: SSI_MARGINAL
$env:AUCTION_ALGORITHM="SSI_MARGINAL"
python multi_agent_runner.py --scenario deadlock
```

### Kịch Bản 3: Continuous Shift Stress (30 phút)

Kiểm tra với tải cao:

```bash
cd agv-system/tests/simulators

$env:SIM_SCENARIO_SEED="42"
$env:SIM_TIME_SCALE="0.1"

# Run 1: GREEDY_DISTANCE
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"
python multi_agent_runner.py --scenario continuous_shift_stress_30m

# Run 2: GREEDY_ETA
$env:AUCTION_ALGORITHM="GREEDY_ETA"
python multi_agent_runner.py --scenario continuous_shift_stress_30m

# Run 3: SSI_MARGINAL
$env:AUCTION_ALGORITHM="SSI_MARGINAL"
python multi_agent_runner.py --scenario continuous_shift_stress_30m
```

---

## 📊 Phân Tích Kết Quả

### Các Chỉ Số Chính

File `*_fleet_summary.csv` chứa các chỉ số:

| Chỉ Số | Tối Ưu | Giải Thích |
|---|---|---|
| **Throughput (tasks/min)** | ↑ Cao | Số task hoàn thành/phút |
| **Makespan (s)** | ↓ Thấp | Thời gian từ task đầu → task cuối |
| **Avg Flow Time (s)** | ↓ Thấp | Thời gian trung bình per task |
| **Energy/Task (%)** | ↓ Thấp | Tiêu hao pin trung bình/task |
| **CV Distance** | ↓ Thấp | Cân bằng tải (0 = hoàn hảo) |
| **Avg Bidding Time (ms)** | ↓ Thấp | Overhead đấu thầu |

### So Sánh Nhanh Với Python

```python
import pandas as pd

# Đọc kết quả từ 3 phương pháp
greedy_dist = pd.read_csv('results/continuous_shift/continuous_shift_XXXXX_fleet_summary.csv', index_col=0)
greedy_eta = pd.read_csv('results/continuous_shift/continuous_shift_XXXXX_fleet_summary.csv', index_col=0)
ssi = pd.read_csv('results/continuous_shift/continuous_shift_XXXXX_fleet_summary.csv', index_col=0)

# Tạo bảng so sánh
comparison = pd.DataFrame({
    'GREEDY_DISTANCE': greedy_dist['value'],
    'GREEDY_ETA': greedy_eta['value'],
    'SSI_MARGINAL': ssi['value']
})

print(comparison[['throughput_tasks_per_min', 'makespan_s', 'avg_flow_time_per_task_s', 'total_energy_consumed_pct']])
```

### Visualize Kết Quả

```bash
cd visualization_tool/scripts
python analysis_plots.py
```

Sinh ra các biểu đồ so sánh tự động.

---

## 🔄 Lặp Thí Nghiệm (Recommended Practice)

Để kết quả thống kê tin cậy, chạy **5+ lần** với seed khác nhau:

```bash
cd agv-system/tests/simulators

$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"
$env:SIM_TIME_SCALE="0.1"

# Seed 42
$env:SIM_SCENARIO_SEED="42"
python multi_agent_runner.py --scenario continuous_shift

# Seed 99
$env:SIM_SCENARIO_SEED="99"
python multi_agent_runner.py --scenario continuous_shift

# Seed 2025
$env:SIM_SCENARIO_SEED="2025"
python multi_agent_runner.py --scenario continuous_shift

# ... (lặp với seed khác)
```

Sau đó tính mean ± std của các chỉ số:

```python
import os
import pandas as pd
from pathlib import Path

results_dir = Path('results/continuous_shift')
all_files = list(results_dir.glob('*_fleet_summary.csv'))

dataframes = []
for f in all_files:
    df = pd.read_csv(f, index_col=0)
    dataframes.append(df)

summary = pd.concat(dataframes, axis=1).T
print(summary[['throughput_tasks_per_min', 'makespan_s']].describe())
# Hiển thị mean, std, min, max
```

---

## 🐛 Khắc Phục Sự Cố

### Lỗi: "API not reachable"

```bash
# Kiểm tra Docker container
docker-compose ps

# Nếu chưa chạy:
docker-compose up -d

# Xem log Django
docker-compose logs web -f
```

### Lỗi: "Unknown AUCTION_ALGORITHM"

```bash
# Kiểm tra giá trị được set
echo $env:AUCTION_ALGORITHM

# Giá trị hợp lệ:
# SSI_MARGINAL, GREEDY_ETA, GREEDY_DISTANCE
```

### Mô Phỏng Quá Lâu

```bash
# Giảm SIM_TIME_SCALE để chạy nhanh hơn
$env:SIM_TIME_SCALE="0.05"  # 20x nhanh hơn
```

### Không Có Kết Quả

```bash
# Kiểm tra thư mục results/
ls results/continuous_shift/

# Xem detailed log
python multi_agent_runner.py --scenario continuous_shift 2>&1 | Tee simulation.log
```

---

## 📝 Lệnh Tóm Tắt (Cheat Sheet)

```bash
# Terminal 1: Start Backend
cd agv-system
docker-compose up -d

# Terminal 2: Run Simulations
cd agv-system/tests/simulators

# GREEDY_DISTANCE
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"; $env:SIM_SCENARIO_SEED="42"; python multi_agent_runner.py --scenario continuous_shift

# GREEDY_ETA
$env:AUCTION_ALGORITHM="GREEDY_ETA"; $env:SIM_SCENARIO_SEED="42"; python multi_agent_runner.py --scenario continuous_shift

# SSI_MARGINAL
$env:AUCTION_ALGORITHM="SSI_MARGINAL"; $env:SIM_SCENARIO_SEED="42"; python multi_agent_runner.py --scenario continuous_shift
```

---

## 🎯 Quy Trình Đề Xuất Cho Luận Văn

### Phase 1: Kiểm Chứng (1 ngày)
1. Chạy 3 phương pháp với seed=42, scenario=continuous_shift
2. Xác nhận kết quả hợp lý (không có lỗi)
3. So sánh số liệu nhanh

### Phase 2: Chính Thức (3-5 ngày)
1. Chạy mỗi phương pháp **5 lần** với seed khác nhau
2. Mỗi scenario: continuous_shift, deadlock, continuous_shift_stress_30m
3. Tính mean ± std
4. Áp dụng statistical test (t-test hoặc Mann-Whitney)

### Phase 3: Análysis (1-2 ngày)
1. Vẽ biểu đồ so sánh
2. Phân tích các điểm yếu/mạnh
3. Viết kết luận

---

## 📚 Tham Khảo

- [ALGORITHM_COMPARISON_SSI_VS_GREEDY.md](ALGORITHM_COMPARISON_SSI_VS_GREEDY.md) - So sánh chi tiết từng phương pháp
- [backend/vda5050/modules/constant.py](../backend/vda5050/modules/constant.py) - Cấu hình mặc định
- [tests/simulators/scenarios.py](../tests/simulators/scenarios.py) - Định nghĩa kịch bản

---

**Lưu ý**: Cách chạy **vẫn giống hệt như trước**, chỉ sử dụng environment variable `AUCTION_ALGORITHM`. Hiện tại bạn đã tách GREEDY_DISTANCE và GREEDY_ETA thành code độc lập, không chia sẻ logic với SSI.

# Cheat Sheet - Chạy Mô Phỏng So Sánh Auction

## ⚡ Chạy Nhanh (1 dòng lệnh)

### GREEDY_DISTANCE
```powershell
cd agv-system/tests/simulators
$env:AUCTION_ALGORITHM="GREEDY_DISTANCE"; $env:SIM_SCENARIO_SEED="42"; python multi_agent_runner.py --scenario continuous_shift
```

### GREEDY_ETA
```powershell
$env:AUCTION_ALGORITHM="GREEDY_ETA"; $env:SIM_SCENARIO_SEED="42"; python multi_agent_runner.py --scenario continuous_shift
```

### SSI_MARGINAL
```powershell
$env:AUCTION_ALGORITHM="SSI_MARGINAL"; $env:SIM_SCENARIO_SEED="42"; python multi_agent_runner.py --scenario continuous_shift
```

---

## 🚀 Chạy Cả 3 Phương Pháp (Tự Động)

```powershell
cd agv-system/tests/simulators
.\run_comparison.ps1 -Scenario continuous_shift -Seed 42 -Algorithm all
```

### Các Tùy Chọn:
```powershell
# Chạy với scenario khác
.\run_comparison.ps1 -Scenario deadlock

# Chạy với seed khác
.\run_comparison.ps1 -Seed 99

# Chạy chỉ một phương pháp
.\run_comparison.ps1 -Algorithm GREEDY_DISTANCE
.\run_comparison.ps1 -Algorithm GREEDY_ETA
.\run_comparison.ps1 -Algorithm SSI_MARGINAL

# Kết hợp
.\run_comparison.ps1 -Scenario continuous_shift_stress_30m -Seed 42 -Algorithm all
```

---

## 📊 Các Scenario Có Sẵn

| Scenario | Mô Tả | Thích Hợp Để Test |
|---|---|---|
| `continuous_shift` | 30 phút hoạt động liên tục | Endurance, battery cycling |
| `deadlock` | Tắc nghẽn ngắn hạn | Stability, deadlock handling |
| `continuous_shift_stress_30m` | 30 phút với task đột ngột | Stress test, load balancing |

---

## 🔄 Lặp Thí Nghiệm (5 Seeds)

```powershell
cd agv-system/tests/simulators

foreach ($seed in 42, 99, 2025, 12345, 54321) {
    Write-Host "`n>>> Running with Seed=$seed" -ForegroundColor Cyan
    .\run_comparison.ps1 -Scenario continuous_shift -Seed $seed -Algorithm all
    Start-Sleep -Seconds 3
}
```

---

## 🔍 Xem Kết Quả

```bash
# Liệt kê tất cả kết quả
ls results/continuous_shift/

# Xem fleet summary của GREEDY_DISTANCE
head -20 results/continuous_shift/*GREEDY_DISTANCE*_fleet_summary.csv

# So sánh ba phương pháp (Python)
python3 << 'EOF'
import pandas as pd
import glob

files = glob.glob("results/continuous_shift/*_fleet_summary.csv")
for f in files:
    df = pd.read_csv(f, index_col=0)
    algo = "GREEDY_DISTANCE" if "GREEDY_DISTANCE" in f else \
           "GREEDY_ETA" if "GREEDY_ETA" in f else "SSI_MARGINAL"
    print(f"\n{algo}:")
    print(df.loc[['throughput_tasks_per_min', 'makespan_s', 'avg_flow_time_per_task_s']])
EOF
```

---

## ⚙️ Cấu Hình Nâng Cao

### Thay Đổi Epsilon (SSI_MARGINAL)
```powershell
# epsilon=0: MiniMax (fairness)
$env:AUCTION_ALGORITHM="SSI_MARGINAL"; python multi_agent_runner.py --scenario continuous_shift --epsilon 0.0

# epsilon=0.5: Balanced
$env:AUCTION_ALGORITHM="SSI_MARGINAL"; python multi_agent_runner.py --scenario continuous_shift --epsilon 0.5

# epsilon=1: MiniSum (efficiency)
$env:AUCTION_ALGORITHM="SSI_MARGINAL"; python multi_agent_runner.py --scenario continuous_shift --epsilon 1.0
```

### Thay Đổi Time Scale (Chạy Nhanh/Chậm)
```powershell
# Chạy 2x nhanh
$env:SIM_TIME_SCALE="0.05"; python multi_agent_runner.py --scenario continuous_shift

# Chạy bình thường
$env:SIM_TIME_SCALE="0.1"; python multi_agent_runner.py --scenario continuous_shift

# Chạy chậm (real-time)
$env:SIM_TIME_SCALE="1.0"; python multi_agent_runner.py --scenario continuous_shift
```

---

## 🛠️ Kiểm Tra & Khắc Phục

```bash
# Kiểm tra Backend có chạy không
curl http://localhost:8000/api/agvs/ -s | head -5

# Xem container logs
docker-compose logs -f web

# Restart Backend
docker-compose down
docker-compose up -d

# Xem chi tiết simulation log
python multi_agent_runner.py --scenario continuous_shift 2>&1 | Tee sim.log
```

---

## 📋 Danh Sách Biến Môi Trường

| Biến | Giá Trị | Ví Dụ |
|---|---|---|
| `AUCTION_ALGORITHM` | String | `SSI_MARGINAL`, `GREEDY_ETA`, `GREEDY_DISTANCE` |
| `SIM_SCENARIO_SEED` | Integer | `42`, `99`, `2025` |
| `SIM_TIME_SCALE` | Float | `0.1`, `1.0` |

---

## 📈 Phân Tích Kết Quả Với Python

```python
import pandas as pd
import glob

# Đọc tất cả fleet summary
files = sorted(glob.glob("results/continuous_shift/*_fleet_summary.csv"))

data = {}
for f in files:
    df = pd.read_csv(f, index_col=0)
    algo = "GREEDY_DISTANCE" if "GREEDY_DISTANCE" in f else \
           "GREEDY_ETA" if "GREEDY_ETA" in f else "SSI_MARGINAL"
    data[algo] = df

# Tạo bảng so sánh
metrics = ['throughput_tasks_per_min', 'makespan_s', 'avg_flow_time_per_task_s', 'total_energy_consumed_pct']
comparison = {}
for metric in metrics:
    comparison[metric] = {algo: data[algo].loc[metric, 'value'] for algo in data}

result = pd.DataFrame(comparison).T
print(result)
print("\nBest (↑ tốt hơn):")
print(result.idxmin(axis=1))
```

---

## 📝 Workflow Đề Xuất Cho Luận Văn

### Ngày 1-2: Kiểm Chứng Prototype
```bash
# Chạy nhanh kiểm tra code không lỗi
.\run_comparison.ps1 -Scenario continuous_shift -Seed 42
```

### Ngày 3-5: Thu Thập Dữ Liệu
```bash
# Chạy 5 seeds (mỗi lần ~30 phút)
foreach ($seed in 42, 99, 2025, 12345, 54321) {
    .\run_comparison.ps1 -Scenario continuous_shift -Seed $seed -Algorithm all
}
```

### Ngày 6-7: Phân Tích & Visualization
```bash
# Python script để tính mean ± std
cd ../../visualization_tool/scripts
python analysis_plots.py

# Vẽ biểu đồ so sánh
python3 plot_comparison.py
```

---

## 🎯 Cách Thành Công

✅ **Trước khi chạy:**
- ✓ Backend (Docker) đang chạy (`docker-compose ps`)
- ✓ API accessible (`curl http://localhost:8000/api/agvs/`)
- ✓ Ở trong thư mục `agv-system/tests/simulators/`

✅ **Sau khi chạy:**
- ✓ Files xuất ra trong `results/`
- ✓ Không có lỗi trong terminal
- ✓ Có thể xem metrics từ CSV

✅ **Khi so sánh:**
- ✓ Dùng cùng seed cho 3 phương pháp
- ✓ Dùng cùng scenario
- ✓ Chạy 5+ lần để có ý nghĩa thống kê

---

**⏱️ Thời Gian Dự Kiến:**
- 1 lần chạy (1 phương pháp, 1 scenario): ~5-15 phút (tùy scenario)
- 3 phương pháp × 1 scenario: ~30 phút
- 3 phương pháp × 5 seeds: ~2.5 giờ
- Phân tích & visualization: ~1 giờ

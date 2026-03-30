# Bidding System Module

## 🏗️ System Architecture

### 1. **BiddingEngine** (Facade Pattern)
- **File**: `bidding/engine.py`
- **Vai trò**: Main interface for external modules
- **Functions**:
  - Khởi tạo và quản lý tất cả components
  - Cung cấp API đơn giản: `run_auction()`, `run_auction_with_details()`
  - Backward compatibility với code cũ

### 2. **AuctionCoordinator**
- **File**: `bidding/auction.py`
- **Vai trò**: Điều phối quá trình đấu giá
- **Chức năng**:
  - Lấy danh sách AGV khả dụng
  - Thu thập bids từ tất cả AGV
  - Chọn winner (bid thấp nhất)
  - Logging chi tiết

### 3. **Calculators Package**

#### 3.1 TransportCalculator
- **File**: `bidding/calculators/transport.py`
- **Vai trò**: Tính toán metrics vật lý
- **Functions**:
  - `calculate_travel_time()`: Travel time
  - `calculate_energy_consumption()`: Energy consumed
  - `calculate_metrics()`: Tính cả E và T
  - `validate_metrics()`: Kiểm tra giá trị hợp lệ

#### 3.2 BaselineCalculator
- **File**: `bidding/calculators/baseline.py`
- **Vai trò**: Tính toán baseline normalization
- **Chức năng**:
  - `calculate_baseline_distance()`: Khoảng cách lý tưởng (Dijkstra)
  - `calculate_baseline_metrics()`: Energy/Time baseline
  - `normalize_metrics()`: Chuẩn hóa so với baseline
  - `calculate_and_normalize()`: All-in-one

#### 3.3 BidCalculator
- **File**: `bidding/calculators/bid.py`
- **Vai trò**: Tính toán giá thầu cho AGV
- **Chức năng**:
  - `get_agv_current_state()`: Lấy state hiện tại
  - `check_battery_constraint()`: Kiểm tra ràng buộc pin
  - `calculate_wait_cost()`: Chi phí chờ nếu bận
  - `calculate_marginal_cost()`: Chi phí biên
  - `calculate_bid_score()`: Hybrid Objective scoring
  - `calculate_full_bid()`: Tính toán đầy đủ

## 📖 Cách sử dụng

### Cách 1: Sử dụng BiddingEngine (Recommended)

```python
from vda5050.modules.bidding import BiddingEngine

# Khởi tạo
engine = BiddingEngine()

# Chạy auction cơ bản
winner_agv, error = engine.run_auction(
    target_node_id="N10",
    load_kg=100
)

if winner_agv:
    print(f"Winner: {winner_agv.serial_number}")
else:
    print(f"Auction failed: {error}")

# Chạy auction với chi tiết đầy đủ
result = engine.run_auction_with_details(
    target_node_id="N10",
    load_kg=100
)

print(f"Winner: {result['winner_agv']}")
print(f"All bids: {result['all_bids']}")
```

### Cách 2: Sử dụng Components riêng lẻ (Advanced)

```python
from vda5050.modules.bidding import (
    TransportCalculator,
    BaselineCalculator,
    BidCalculator,
    AuctionCoordinator
)

# Tính toán transport metrics
transport = TransportCalculator()
energy, time = transport.calculate_metrics(distance_m=100, load_kg=50)

# Tính baseline normalization
baseline = BaselineCalculator()
norm_energy, norm_time = baseline.normalize_metrics(
    actual_energy_kj=10.5,
    actual_time_s=50.0,
    baseline_energy_kj=10.0,
    baseline_time_s=45.0
)

# Tính bid cho một AGV
bid_calc = BidCalculator()
bid_result = bid_calc.calculate_full_bid(agv, "N10", load_kg=100)

# Điều phối auction
coordinator = AuctionCoordinator()
winner, error = coordinator.run_auction("N10", load_kg=100)
```

## 🔄 Migration Guide
### How migration:
```python
from vda5050.modules.bidding import BiddingEngine

engine = BiddingEngine()

# Truy cập components
transport = engine.get_transport_calculator()
baseline = engine.get_baseline_calculator()
bid_calc = engine.get_bid_calculator()
coordinator = engine.get_auction_coordinator()

# Sử dụng advanced features
energy, time = transport.calculate_metrics(100, 50)
```

## 📝 TODO / Future Enhancements

1. **MiniMax Improvement**: Implement proper cumulative energy tracking
2. **Dynamic Pricing**: Thêm time-dependent pricing
3. **Multi-Objective**: Optimize cho nhiều objectives (energy, time, fairness)
4. **Machine Learning**: Học từ historical data để cải thiện scoring
5. **Distributed Auction**: Support cho multi-region auctions
6. **Real-time Rebalancing**: Tự động cân bằng tải khi cần

## 🐛 Debugging

Enable debug logging:
```python
import logging
logging.getLogger('vda5050.modules.bidding').setLevel(logging.DEBUG)
```

## 📚 References

- **Algorithm**: SSI-DMAS (Sequential Single Item - Delegate Multi Agent System)
- **Pattern**: Facade, Strategy, Dependency Injection
- **Standards**: VDA5050, PEP8

---

**Version**: 2.0.0  
**Last Updated**: 2026-01-06  
**Author**: Nghia Nguyen

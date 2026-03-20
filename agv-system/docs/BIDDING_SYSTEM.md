# Bidding System Documentation

## 📋 Tổng quan

Hệ thống bidding (đấu thầu) trong AGV Fleet Management sử dụng **auction-based task allocation** để phân bổ transport orders cho AGVs một cách tối ưu. Mỗi khi có order mới, hệ thống thu thập bids từ tất cả AGVs online và chọn AGV có chi phí thấp nhất.

## 🏗️ Kiến trúc

```
TaskViewSet (API)
    ↓
BiddingEngine.run_auction()
    ↓
AuctionCoordinator.run_auction()
    ↓
├─→ collect_bids() ──→ BidCalculator.calculate_marginal_cost()
│                           ↓
│                      ├─→ get_agv_current_state()
│                      ├─→ check_battery_constraint()
│                      ├─→ calculate_wait_cost()    ← Xét active tasks
│                      ├─→ calculate 2-leg cost
│                      └─→ normalize với baseline
│
└─→ evaluate_bids() ──→ Chọn winner, tạo order
```

## 🔑 Core Components

### 1. BiddingEngine (`backend/vda5050/modules/bidding/engine.py`)

Entry point cho auction process.

```python
class BiddingEngine:
    def run_auction(self, pickup_node_id, delivery_node_id=None, 
                    load_kg=DEFAULT_LOAD_KG):
        """
        Chạy auction cho transport order mới.
        
        Args:
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng
            load_kg: Tải trọng (kg)
            
        Returns:
            dict: {'winner': str, 'cost': float} hoặc None
        """
```

### 2. AuctionCoordinator (`backend/vda5050/modules/bidding/auction.py`)

Orchestrate auction process: collect bids, evaluate, select winner.

**Key Methods**:
- `collect_bids()`: Lấy bids từ tất cả AGVs online
- `evaluate_bids()`: Chọn winner dựa trên hybrid MiniSum/MiniMax objective
- `run_auction()`: Full auction flow

### 3. BidCalculator (`backend/vda5050/modules/bidding/calculators/bid.py`)

Tính toán chi phí marginal cho mỗi AGV.

**Key Methods**:
- `get_agv_current_state()`: Lấy node hiện tại và battery
- `check_battery_constraint()`: Kiểm tra battery đủ không
- `calculate_wait_cost()`: **Tính wait time nếu AGV đang bận** ⭐
- `calculate_marginal_cost()`: Tính tổng chi phí (energy + time)

## ⭐ Wait Cost Calculation (Xét Active Tasks)

### Tại sao cần Wait Cost?

Khi AGV đang thực hiện order, nó không thể nhận order mới ngay. Bidding system phải:
1. Tính thời gian còn lại để hoàn thành order hiện tại
2. Tính chi phí từ endpoint của order cũ đến pickup của order mới
3. Tăng total cost để giảm khả năng AGV bận được chọn

### Implementation

```python
def calculate_wait_cost(self, agv, current_node, load_kg):
    """
    Tính chi phí chờ (wait cost) nếu AGV đang bận.
    
    Returns:
        dict: {
            'start_node': str,      # Node AGV sẽ rảnh
            'wait_time_s': float    # Thời gian phải đợi
        }
    """
    # Tìm active order gần nhất
    active_order = Order.objects.filter(
        agv=agv, 
        status__in=['SENT', 'ACTIVE', 'QUEUED']
    ).last()
    
    start_node = current_node
    wait_time = 0.0
    
    if active_order:
        # AGV đang bận: Lấy endpoint của order cũ
        end_node = active_order.nodes[-1]['nodeId']
        start_node = end_node
        
        # Ước tính thời gian còn lại
        remaining_distance = self.graph_engine.get_path_cost(
            current_node, end_node
        )
        
        if remaining_distance != float('inf'):
            _, wait_time = self.transport_calculator.calculate_metrics(
                remaining_distance, load_kg
            )
    
    return {
        'start_node': start_node,
        'wait_time_s': wait_time
    }
```

### Flow khi AGV đang bận

**Scenario**: AGV_01 đang thực hiện Order_A (Node_B → Node_D), order mới cần Node_E → Node_F.

```
1. Current state: AGV_01 at Node_C (đang di chuyển)
   
2. calculate_wait_cost():
   - Tìm active_order: Order_A
   - end_node = Node_D (endpoint của Order_A)
   - remaining_distance = distance(Node_C → Node_D) = 1 edge
   - wait_time = 1 edge × time_per_edge ≈ 1 second
   
3. calculate_marginal_cost():
   - start_node = Node_D (không phải Node_C!)
   - Leg 1: Node_D → Node_E (pickup)
   - Leg 2: Node_E → Node_F (delivery)
   - total_time = wait_time + leg1_time + leg2_time
   
4. Normalized cost:
   - AGV_01_cost = (energy_total, time_total_with_wait)
   - AGV_02_cost = (energy_total, time_total_no_wait)
   → AGV_02 có time thấp hơn → được ưu tiên
```

## 📐 Cost Calculation Formula

### 2-Leg Trip Cost

Với order từ **pickup_node** → **delivery_node**:

```python
# Leg 1: current/end_node → pickup (empty)
distance_leg1 = graph.get_path_cost(start_node, pickup_node)
energy_leg1, time_leg1 = calculator.calculate_metrics(distance_leg1, load_kg=0)

# Leg 2: pickup → delivery (loaded)
distance_leg2 = graph.get_path_cost(pickup_node, delivery_node)
energy_leg2, time_leg2 = calculator.calculate_metrics(distance_leg2, load_kg)

# Total
energy_marginal = energy_leg1 + energy_leg2
time_marginal = wait_time + time_leg1 + time_leg2
```

### Normalization với Baseline

Để so sánh công bằng giữa AGVs ở vị trí khác nhau:

```python
# Baseline: Khoảng cách trực tiếp từ start đến delivery
baseline_distance = graph.get_path_cost(start_node, delivery_node)
baseline_energy, baseline_time = calculator.calculate_metrics(
    baseline_distance, load_kg
)

# Normalized cost
norm_energy = energy_marginal / baseline_energy
norm_time = time_marginal / baseline_time

# Hybrid objective (MiniSum + MiniMax)
combined_cost = ALPHA * norm_energy + (1 - ALPHA) * norm_time
```

**ALPHA = 0.5**: Balance giữa energy efficiency và time efficiency.

## 🎯 Bid Evaluation & Winner Selection

### Hybrid Objective

```python
def evaluate_bids(self, bids):
    """
    Chọn winner dựa trên hybrid MiniSum/MiniMax objective.
    
    MiniSum: Minimize tổng cost của tất cả tasks
    MiniMax: Minimize max cost của AGV nào cũng có
    """
    valid_bids = [b for b in bids if b['cost']['is_valid']]
    
    if not valid_bids:
        return None
    
    # Sort by normalized combined cost (energy + time)
    sorted_bids = sorted(
        valid_bids, 
        key=lambda b: b['cost']['norm_energy'] + b['cost']['norm_time']
    )
    
    return sorted_bids[0]
```

### Winner Criteria

AGV được chọn nếu:
1. ✅ Battery đủ để thực hiện cả 2 legs
2. ✅ Có path đến cả pickup và delivery nodes
3. ✅ Combined cost (energy + time) thấp nhất
4. ✅ Nếu bằng nhau: AGV với battery cao hơn được ưu tiên

## 📊 Metrics & Logging

### Debug Logging

```python
logger.debug(f"AGV {agv.serial_number} bid:")
logger.debug(f"  - Start node: {start_node}")
logger.debug(f"  - Wait time: {wait_time:.2f}s")
logger.debug(f"  - Leg 1: {start_node}→{pickup} = {distance_leg1} edges")
logger.debug(f"  - Leg 2: {pickup}→{delivery} = {distance_leg2} edges")
logger.debug(f"  - Energy: {energy_marginal:.2f} (norm: {norm_energy:.2f})")
logger.debug(f"  - Time: {time_marginal:.2f}s (norm: {norm_time:.2f})")
```

### Bid Structure

```python
{
    'agv_serial': 'AGV_01',
    'cost': {
        'energy_marginal': 45.2,      # Wh
        'time_marginal': 12.5,        # seconds
        'norm_energy': 1.15,          # normalized
        'norm_time': 1.08,            # normalized
        'is_valid': True
    }
}
```

## 🔄 Full Auction Flow Example

### Scenario: Order mới Node_A → Node_C (10kg)

```
1. API Request:
   POST /api/tasks/
   {
       "pickup_node_id": "Node_A",
       "delivery_node_id": "Node_C",
       "load_kg": 10
   }

2. BiddingEngine.run_auction():
   - coordinator.run_auction(Node_A, Node_C, 10)

3. AuctionCoordinator.collect_bids():
   AGVs online: AGV_01, AGV_02, AGV_03
   
   AGV_01 (at Node_B, battery 95%, idle):
     - start_node = Node_B (no wait)
     - Leg 1: Node_B → Node_A (1 edge, empty)
     - Leg 2: Node_A → Node_C (2 edges, 10kg)
     - Cost: (energy=25.5, time=8.0, norm_e=1.05, norm_t=1.02)
   
   AGV_02 (at Node_D, battery 90%, active):
     - active_order ends at Node_E
     - start_node = Node_E (wait 3s)
     - Leg 1: Node_E → Node_A (1 edge, empty)
     - Leg 2: Node_A → Node_C (2 edges, 10kg)
     - Cost: (energy=25.5, time=11.0, norm_e=1.05, norm_t=1.40) ← higher time
   
   AGV_03 (at Node_H, battery 65%, idle):
     - start_node = Node_H
     - Leg 1: Node_H → Node_A (4 edges, empty)
     - Leg 2: Node_A → Node_C (2 edges, 10kg)
     - Cost: (energy=42.0, time=15.0, norm_e=1.72, norm_t=1.91) ← far away

4. evaluate_bids():
   - AGV_01: combined_cost = 1.05 + 1.02 = 2.07 ← WINNER
   - AGV_02: combined_cost = 1.05 + 1.40 = 2.45 (busy)
   - AGV_03: combined_cost = 1.72 + 1.91 = 3.63 (far + low battery)

5. create_transport_order(AGV_01, Node_A, Node_C):
   - Order_XYZ assigned to AGV_01
   - MQTT publish order to AGV_01
   - Database: Order status = SENT
```

## 🎯 Optimization Strategies

### 1. Battery Constraint
```python
BATTERY_RESERVE = 20.0  # Keep 20% reserve
MIN_BATTERY = 30.0      # Reject if <30%

if battery < MIN_BATTERY or remaining_battery < BATTERY_RESERVE:
    return None  # Cannot bid
```

### 2. Wait Time Penalty
AGVs đang bận tự động có cost cao hơn do wait_time được cộng vào total time.

### 3. Distance Normalization
Baseline normalization đảm bảo AGVs ở vị trí khác nhau có thể so sánh công bằng.

### 4. Hybrid Objective
ALPHA=0.5 balance giữa:
- Energy efficiency (economic)
- Time efficiency (throughput)

## 📈 Performance Metrics

### Load Balancing với Active Task Consideration

**Test**: 10 tasks, 7 AGVs, interval 5s

```
With wait cost:
- CV: 35.36% (Fair)
- Active AGVs: 5/7
- Distribution: Relatively even

Without wait cost (hypothetical):
- CV: >60% (Poor)
- Active AGVs: 3/7
- Distribution: Few AGVs overloaded
```

### Throughput Impact

```
Sequential (without gradual sending):
- 10 tasks in 5s
- AGVs không kịp update state
- Many tasks to same AGV

Gradual (with 5s interval):
- 10 tasks in 50s
- AGVs update state after each order
- Better distribution
```

## 🛠️ Configuration

### Tunable Parameters

```python
# backend/vda5050/modules/constant.py
DEFAULT_LOAD_KG = 10.0          # Default load weight
ALPHA = 0.5                     # Energy vs Time weight
BATTERY_RESERVE = 20.0          # Safety reserve
MIN_BATTERY = 30.0              # Min to accept bid

# backend/vda5050/modules/bidding/calculators/transport.py
DEFAULT_SPEED = 1.0             # m/s
DEFAULT_ENERGY_PER_METER = 0.5  # Wh/m
LOADED_ENERGY_FACTOR = 1.5      # 50% increase with load
```

## 📚 Related Files

- [BiddingEngine](../backend/vda5050/modules/bidding/engine.py)
- [AuctionCoordinator](../backend/vda5050/modules/bidding/auction.py)
- [BidCalculator](../backend/vda5050/modules/bidding/calculators/bid.py)
- [TransportCalculator](../backend/vda5050/modules/bidding/calculators/transport.py)
- [BaselineCalculator](../backend/vda5050/modules/bidding/calculators/baseline.py)
- [MULTI_AGV_GUIDE.md](./MULTI_AGV_GUIDE.md)

## 🎓 References

- [VDA5050 Protocol](https://github.com/VDA5050/VDA5050)


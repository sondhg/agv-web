# API Client Testing Guide

## Phase 1, Task 1.1: Extended API Client

### What Was Added

The following TypeScript types and functions were added to `/src/lib/api.ts`:

#### **New Types**

1. `VDA5050Node` - Represents a waypoint in AGV path
2. `VDA5050Edge` - Represents a path segment between nodes
3. `OrderStatus` - Order lifecycle states (CREATED, SENT, ACTIVE, etc.)
4. `Order` - Complete transport order structure
5. `TaskRequest` - Request format for creating tasks
6. `TaskResponse` - Response from auction system
7. `AGVState` - AGV telemetry data

#### **New API Functions**

1. `createTask(task)` - Create transport task, triggers auction
2. `fetchOrders()` - Get all orders
3. `fetchOrder(orderId)` - Get single order
4. `fetchAgvStates(serialNumber)` - Get AGV state history

---

## Testing Instructions

### Prerequisites

1. **Backend must be running**:

   ```bash
   cd agv-system
   docker-compose up -d
   ```

2. **Test data must be setup**:

   ```bash
   docker-compose exec web python manage.py setup_test_agvs --count 7
   docker-compose exec web python manage.py setup_test_graph
   ```

3. **AGV simulators should be running**:

   ```bash
   cd tests/simulators
   python multi_mock_agv.py
   ```

4. **Frontend should be running**:
   ```bash
   cd agv-gui
   pnpm dev
   ```

---

## Manual Testing (Browser Console)

Open your browser to `http://localhost:5173` and open the browser console (F12).

### Test 1: Fetch All Orders

```javascript
// Copy and paste into browser console
const response = await fetch("http://localhost:8000/api/orders/")
const orders = await response.json()
console.log("Orders:", orders)
```

**Expected result**: Array of orders (may be empty if no tasks created yet)

**Success criteria**:

- ✅ No error thrown
- ✅ Returns array (even if empty)
- ✅ Each order has: `id`, `order_id`, `status`, `nodes`, `edges`

---

### Test 2: Fetch Graph Nodes

```javascript
// This is needed to know which nodes exist for task creation
const response = await fetch("http://localhost:8000/api/graph/nodes/")
const nodes = await response.json()
console.log(
  "Available nodes:",
  nodes.map((n) => n.node_id)
)
```

**Expected result**: Array of node objects

**Success criteria**:

- ✅ Returns array with 8 nodes (from setup_test_graph)
- ✅ Example nodes: "Node_A", "Node_B", "Node_C", etc.

---

### Test 3: Create a Transport Task (CORE FUNCTIONALITY)

```javascript
// Create a transport task from Node_A to Node_C
const response = await fetch("http://localhost:8000/api/tasks/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    pickup_node_id: "Node_A",
    delivery_node_id: "Node_C",
  }),
})

const result = await response.json()
console.log("Auction result:", result)
```

**Expected result**: Object with auction winner

**Success criteria**:

- ✅ `success: true`
- ✅ `winner_agv` is a serial number (e.g., "AGV_01")
- ✅ `order_id` is generated (e.g., "ORD_A3F2B8C1")
- ✅ `status` is "CREATED" or "QUEUED"
- ✅ `path` is an array of node IDs
- ✅ `pickup_node` is "Node_A"
- ✅ `delivery_node` is "Node_C"

**Example response**:

```json
{
  "success": true,
  "order_id": "ORD_A3F2B8C1",
  "winner_agv": "AGV_01",
  "status": "CREATED",
  "message": "Order sent to AGV",
  "pickup_node": "Node_A",
  "delivery_node": "Node_C",
  "path": ["Node_B", "Node_A", "Node_C"]
}
```

---

### Test 4: Verify Order Was Created

```javascript
// Fetch orders again to see the new order
const response = await fetch("http://localhost:8000/api/orders/")
const orders = await response.json()
console.log("Total orders:", orders.length)
console.log("Latest order:", orders[0]) // Newest first
```

**Expected result**: Array contains the order you just created

**Success criteria**:

- ✅ At least 1 order exists
- ✅ Latest order has the `order_id` from Test 3
- ✅ Order has `nodes` array (should have 3+ nodes: current → pickup → delivery)
- ✅ Order has `edges` array (connections between nodes)

---

### Test 5: Fetch AGV States

```javascript
// Get telemetry data for AGV_01
const response = await fetch("http://localhost:8000/api/agvs/AGV_01/states/")
const states = await response.json()
console.log("AGV_01 state count:", states.length)
console.log("Latest state:", states[0]) // Newest first
```

**Expected result**: Array of state snapshots

**Success criteria**:

- ✅ Returns array of states
- ✅ Each state has: `battery_state`, `agv_position`, `velocity`, `safety_state`
- ✅ `battery_state.batteryCharge` is a number (0-100)
- ✅ `agv_position.x` and `agv_position.y` are numbers
- ✅ `driving` is a boolean

---

### Test 6: Check AGV Online Status

```javascript
// See which AGVs are online
const response = await fetch("http://localhost:8000/api/agvs/")
const agvs = await response.json()
console.log(
  "AGVs online:",
  agvs.filter((a) => a.is_online).map((a) => a.serial_number)
)
console.log(
  "AGVs offline:",
  agvs.filter((a) => !a.is_online).map((a) => a.serial_number)
)
```

**Expected result**: List of online/offline AGVs

**Success criteria**:

- ✅ If simulators are running, several AGVs should be `is_online: true`
- ✅ If simulators are NOT running, all AGVs will be `is_online: false`

---

## Troubleshooting

### Error: "Failed to fetch"

**Cause**: Backend is not running or CORS is not configured

**Fix**:

```bash
# Check backend is running
docker-compose ps

# Check backend logs
docker-compose logs web
```

---

### Error: "No suitable AGV found"

**Cause**: No AGVs are online

**Fix**: Start the AGV simulators

```bash
cd agv-system/tests/simulators
python multi_mock_agv.py
```

Wait 10 seconds for AGVs to connect, then try creating a task again.

---

### Error: "Node not found"

**Cause**: Graph nodes don't exist in database

**Fix**:

```bash
cd agv-system
docker-compose exec web python manage.py setup_test_graph
```

---

## Verification Checklist

After running all tests, confirm:

- [ ] ✅ Test 1: Can fetch orders (even if empty)
- [ ] ✅ Test 2: Can fetch graph nodes (8 nodes exist)
- [ ] ✅ Test 3: Can create task and get auction result
- [ ] ✅ Test 4: Created order appears in orders list
- [ ] ✅ Test 5: Can fetch AGV states
- [ ] ✅ Test 6: Can see AGV online status

---

## Next Steps

Once all tests pass, you're ready for:

**Phase 1, Task 1.2**: Create the Task Assignment Page (UI)

This will provide a user interface for creating tasks instead of using the browser console.

---

## Notes

- The API client uses TypeScript interfaces that exactly match the Django backend models
- All functions include proper error handling with descriptive error messages
- The `createTask()` function is the core of the auction system - it triggers the bidding algorithm
- Order status will change automatically: CREATED → SENT → ACTIVE → COMPLETED
- You can monitor status changes by fetching orders repeatedly (we'll add auto-refresh in the UI later)

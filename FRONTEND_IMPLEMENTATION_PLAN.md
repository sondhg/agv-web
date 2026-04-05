# AGV Fleet Management System - Frontend Implementation Plan

## 🎯 Project Goal
Create a **functional web application** for warehouse operators to:
1. Monitor AGV fleet in real-time
2. Assign transport tasks using the auction-based bidding system
3. Verify smart scheduling and task allocation algorithms
4. Control AGV operations (pause, resume, cancel)

**Focus**: Make it work first. UI polish comes later.

---

## ✅ Already Implemented

### 1. AGV Fleet Registration (`/register-agvs`)
- ✅ CSV import of AGV fleet data
- ✅ Display AGV list in data table
- ✅ API integration: `fetchAgvs()`, `replaceAllAgvs()`

### 2. Graph Map Editor (`/graph-map`)
- ✅ React Flow integration for visual map editing
- ✅ Create nodes (drag-and-drop positioning)
- ✅ Create edges (connect nodes)
- ✅ API integration: Graph nodes/edges CRUD operations

### 3. API Client (`/lib/api.ts`)
- ✅ AGV management functions
- ✅ Graph management functions (nodes, edges)
- ⚠️ **MISSING**: Task, Order, AGV State APIs

---

## 🚀 Implementation Roadmap

### **Phase 1: Core Task Assignment System (CRITICAL)**

The main value of this project is the **auction-based bidding system**. Operators need to:
1. See which AGVs are available
2. Create transport tasks (pickup → delivery)
3. See which AGV won the auction
4. Verify the algorithm is working correctly

#### **Task 1.1: Extend API Client**
File: `/agv-gui/src/lib/api.ts`

Add missing API functions:

```typescript
// ============================================
// TASK & ORDER API
// ============================================

export interface TaskRequest {
  pickup_node_id: string
  delivery_node_id: string
}

export interface TaskResponse {
  success: boolean
  order_id: string
  winner_agv: string
  status: string
  message: string
  pickup_node: string
  delivery_node: string
  path: string[]
  error?: string
}

export interface Order {
  id: number
  agv: number
  header_id: number
  timestamp: string
  order_id: string
  order_update_id: number
  zone_set_id: string
  status: 'CREATED' | 'SENT' | 'ACTIVE' | 'QUEUED' | 'COMPLETED' | 'REJECTED' | 'CANCELLED' | 'FAILED'
  nodes: VDA5050Node[]
  edges: VDA5050Edge[]
  rejection_reason?: string
  created_at: string
  updated_at: string
}

export interface VDA5050Node {
  nodeId: string
  sequenceId: number
  released: boolean
  actions: any[]
  nodePosition: { x: number, y: number, mapId: string }
}

export interface VDA5050Edge {
  edgeId: string
  sequenceId: number
  startNodeId: string
  endNodeId: string
  released: boolean
  maxSpeed: number
}

export interface AGVState {
  id: number
  header_id: number
  timestamp: string
  order_id: string
  last_node_id: string
  last_node_sequence_id: number
  driving: boolean
  paused: boolean
  operating_mode: string
  battery_state: {
    batteryCharge: number
    batteryVoltage: number
    batteryHealth: number
  }
  agv_position: {
    x: number
    y: number
    theta: number
    mapId: string
    positionInitialized: boolean
  }
  velocity: {
    vx: number
    vy: number
    omega: number
  }
  safety_state: {
    eStop: string
    fieldViolation: boolean
  }
  errors: any[]
  loads: any[]
}

// Create transport task (triggers auction)
export async function createTask(task: TaskRequest): Promise<TaskResponse> {
  const response = await fetch(`${API_BASE_URL}/tasks/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task)
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(`Task creation failed: ${JSON.stringify(errorData)}`)
  }
  
  return response.json()
}

// Fetch all orders
export async function fetchOrders(): Promise<Order[]> {
  const response = await fetch(`${API_BASE_URL}/orders/`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch orders: ${response.statusText}`)
  }
  
  return response.json()
}

// Fetch single order
export async function fetchOrder(orderId: number): Promise<Order> {
  const response = await fetch(`${API_BASE_URL}/orders/${orderId}/`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch order: ${response.statusText}`)
  }
  
  return response.json()
}

// Fetch AGV states (latest 100)
export async function fetchAgvStates(serialNumber: string): Promise<AGVState[]> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/states/`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch AGV states: ${response.statusText}`)
  }
  
  return response.json()
}
```

**Verification**: Test each function manually in browser console after implementation.

---

#### **Task 1.2: Create Task Assignment Page**
File: `/agv-gui/src/app/tasks/create/page.tsx`

**Purpose**: Allow operators to create transport tasks and see auction results.

**Requirements**:
1. Dropdown to select pickup node (from graph)
2. Dropdown to select delivery node (from graph)
3. "Create Task" button
4. Display auction results:
   - Winner AGV serial number
   - Calculated path
   - Order ID
   - Order status
5. Error display if task fails (no AGVs online, no path found, etc.)

**Functionality checklist**:
- [ ] Load graph nodes from API on mount
- [ ] Validate pickup ≠ delivery before submitting
- [ ] Call `createTask()` API
- [ ] Display success/error feedback
- [ ] Show winner AGV prominently
- [ ] Show calculated path as list of nodes
- [ ] Link to order details page

**UI sketch** (functional, not pretty):
```
┌─────────────────────────────────────────┐
│ Create Transport Task                   │
├─────────────────────────────────────────┤
│ Pickup Node:  [Dropdown: Node_A ▼]     │
│ Delivery Node: [Dropdown: Node_C ▼]    │
│                                         │
│ [Create Task]                           │
│                                         │
│ ─── Auction Results ───                 │
│ ✅ Task assigned to: AGV_01             │
│ Order ID: ORD_A3F2B8C1                  │
│ Status: CREATED                         │
│ Path: Node_B → Node_A → Node_C          │
│                                         │
│ [View Order Details]                    │
└─────────────────────────────────────────┘
```

---

#### **Task 1.3: Create Order Tracking Page**
File: `/agv-gui/src/app/tasks/orders/page.tsx`

**Purpose**: Monitor all orders and their execution status.

**Requirements**:
1. Display all orders in a table
2. Columns:
   - Order ID
   - AGV Serial Number
   - Status (badge with color)
   - Created At
   - Updated At
   - Actions (View Details)
3. Auto-refresh every 5 seconds (to see status changes)
4. Filter by status (tabs: All, Active, Completed, Rejected, Failed)
5. Click row to see order details

**Functionality checklist**:
- [ ] Fetch orders on mount
- [ ] Auto-refresh every 5s using `setInterval`
- [ ] Status badge color coding:
  - CREATED: gray
  - SENT: blue
  - ACTIVE: green (pulsing)
  - QUEUED: yellow
  - COMPLETED: green
  - REJECTED/FAILED: red
  - CANCELLED: orange
- [ ] Sort by created_at (newest first)
- [ ] Filter by status
- [ ] Click to view order details modal

**UI sketch**:
```
┌────────────────────────────────────────────────────────────────┐
│ Transport Orders                       [Auto-refresh: ON]      │
├────────────────────────────────────────────────────────────────┤
│ [All] [Active] [Completed] [Rejected] [Failed]                │
├────────────────────────────────────────────────────────────────┤
│ Order ID         AGV      Status     Created       Actions     │
├────────────────────────────────────────────────────────────────┤
│ ORD_A3F2B8C1    AGV_01   🟢 ACTIVE   10:30:00     [Details]   │
│ ORD_B7E1F3D2    AGV_02   🟡 QUEUED   10:29:45     [Details]   │
│ ORD_C2A8D4F1    AGV_01   ✅ COMPLETED 10:28:30    [Details]   │
└────────────────────────────────────────────────────────────────┘
```

---

#### **Task 1.4: Create Order Details Modal**
Component: `/agv-gui/src/components/order-details-modal.tsx`

**Purpose**: Show complete order information for verification.

**Requirements**:
1. Display all order fields
2. Show VDA5050 nodes array
3. Show VDA5050 edges array
4. Show status history (if available)
5. Show rejection reason (if failed)

**Functionality checklist**:
- [ ] Display order metadata (ID, AGV, timestamps)
- [ ] Display nodes with sequence IDs
- [ ] Display edges with sequence IDs
- [ ] Show current status
- [ ] Show rejection_reason if status is REJECTED/FAILED
- [ ] Close button

**UI sketch**:
```
┌────────────────────────────────────────┐
│ Order Details: ORD_A3F2B8C1      [X]  │
├────────────────────────────────────────┤
│ AGV: AGV_01                            │
│ Status: ACTIVE                         │
│ Created: 2024-03-21 10:30:00           │
│ Updated: 2024-03-21 10:30:05           │
│                                        │
│ ─── Path ───                           │
│ 0: Node_B (current position)           │
│ 1: Edge Node_B → Node_A                │
│ 2: Node_A (pickup)                     │
│ 3: Edge Node_A → Node_C                │
│ 4: Node_C (delivery)                   │
│                                        │
│            [Close]                     │
└────────────────────────────────────────┘
```

---

### **Phase 2: Fleet Monitoring (CRITICAL)**

Operators need to see AGV status in real-time to verify the system is working.

#### **Task 2.1: Create Fleet Dashboard Page**
File: `/agv-gui/src/app/fleet/page.tsx`

**Purpose**: Monitor all AGVs, their status, battery, position, and current tasks.

**Requirements**:
1. Display all AGVs in cards/grid
2. Auto-refresh every 3 seconds
3. Show for each AGV:
   - Serial number
   - Online/Offline status
   - Battery level (% and visual bar)
   - Last seen timestamp
   - Current position (node_id or x,y coordinates)
   - Current order (if any)
   - Movement status (driving, paused, idle)
4. Click AGV card to see detailed telemetry

**Functionality checklist**:
- [ ] Fetch AGVs on mount
- [ ] Auto-refresh every 3s
- [ ] For each AGV, fetch latest state (`fetchAgvStates()` → take first item)
- [ ] Display online/offline (check `is_online` field)
- [ ] Display battery with color:
  - Red: <20%
  - Yellow: 20-50%
  - Green: >50%
- [ ] Display last_seen timestamp (format: "2 minutes ago")
- [ ] Display current order_id (from latest state)
- [ ] Display last_node_id (current position)
- [ ] Click to open AGV details modal

**UI sketch**:
```
┌─────────────────────────────────────────────────────────────────┐
│ AGV Fleet Status                       [Auto-refresh: 3s]       │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│ │ AGV_01         │  │ AGV_02         │  │ AGV_03         │    │
│ │ 🟢 ONLINE      │  │ 🟢 ONLINE      │  │ 🔴 OFFLINE     │    │
│ │ ████████░░ 85% │  │ ██████░░░░ 65% │  │ ░░░░░░░░░░ --% │    │
│ │ at Node_B      │  │ at Node_D      │  │ Last: 5m ago   │    │
│ │ 🚚 Driving     │  │ ⏸️  Paused     │  │                │    │
│ │ Order: ORD_... │  │ Order: ORD_... │  │ No active task │    │
│ └────────────────┘  └────────────────┘  └────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

#### **Task 2.2: Create AGV Details Modal**
Component: `/agv-gui/src/components/agv-details-modal.tsx`

**Purpose**: Show detailed telemetry for troubleshooting and verification.

**Requirements**:
1. Display latest AGV state data
2. Show battery details (charge, voltage, health)
3. Show position (x, y, theta, mapId)
4. Show velocity (vx, vy, omega)
5. Show safety state (e-stop, field violations)
6. Show errors (if any)
7. Show loads (if any)
8. Show operating mode

**Functionality checklist**:
- [ ] Fetch latest state for AGV
- [ ] Display all battery_state fields
- [ ] Display all agv_position fields
- [ ] Display velocity data
- [ ] Display safety_state (highlight if e-stop or violations)
- [ ] Display errors array (red if not empty)
- [ ] Display loads array
- [ ] Close button

**UI sketch**:
```
┌────────────────────────────────────────┐
│ AGV Details: AGV_01              [X]  │
├────────────────────────────────────────┤
│ Status: ONLINE (Last seen: 2s ago)     │
│ Operating Mode: AUTOMATIC              │
│                                        │
│ ─── Battery ───                        │
│ Charge: 85.5%                          │
│ Voltage: 48.2V                         │
│ Health: 95%                            │
│                                        │
│ ─── Position ───                       │
│ Map: warehouse_floor1                  │
│ X: 10.5, Y: 20.3, θ: 1.57             │
│ Last Node: Node_B (seq: 5)             │
│                                        │
│ ─── Velocity ───                       │
│ vx: 1.2 m/s, vy: 0.0 m/s              │
│ ω: 0.0 rad/s                          │
│                                        │
│ ─── Safety ───                         │
│ E-Stop: NONE ✅                        │
│ Field Violation: No ✅                 │
│                                        │
│ ─── Errors ───                         │
│ None                                   │
│                                        │
│            [Close]                     │
└────────────────────────────────────────┘
```

---

### **Phase 3: Visualize Fleet on Map (HIGH PRIORITY)**

Operators need to see AGV positions on the warehouse map to verify movement.

#### **Task 3.1: Create Fleet Map Visualization Page**
File: `/agv-gui/src/app/fleet/map/page.tsx`

**Purpose**: Show AGVs moving on the graph map in real-time.

**Requirements**:
1. Display graph (nodes and edges) from database
2. Overlay AGV positions on the map
3. Auto-refresh AGV positions every 2 seconds
4. Show AGV serial number labels
5. Color-code AGVs by status:
   - Green: Online & idle
   - Blue: Online & driving
   - Yellow: Paused
   - Red: Error/offline
6. Click AGV to see details
7. Zoom/pan controls

**Functionality checklist**:
- [ ] Fetch graph (nodes, edges) on mount
- [ ] Render nodes as circles at (x, y) coordinates
- [ ] Render edges as lines between nodes
- [ ] Fetch AGVs on mount
- [ ] For each AGV, fetch latest state
- [ ] Extract agv_position from state
- [ ] Render AGV marker at position
- [ ] Auto-refresh AGV positions every 2s
- [ ] Color AGV markers based on driving/paused/errors
- [ ] Click AGV to open details modal
- [ ] Implement zoom/pan (can reuse React Flow or use plain SVG)

**Implementation options**:
- **Option A**: Reuse React Flow (familiar from map editor)
- **Option B**: Use plain Canvas/SVG for better performance
- **Recommendation**: Start with React Flow, optimize later if slow

**UI sketch**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Fleet Map                                [Refresh: 2s] [Zoom]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│         ○ Node_A ──── ○ Node_B ──── ○ Node_C                   │
│                         │             │                         │
│                         │             │                         │
│         ○ Node_D ──── ○ Node_E ──── ○ Node_F                   │
│                       🟢AGV_01                                  │
│                       (Driving)                                 │
│                                                                 │
│         ○ Node_G ──── ○ Node_H                                 │
│                     🔴AGV_03                                    │
│                     (Offline)                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

#### **Task 3.2: Highlight Active Order Paths**
Enhancement to Fleet Map

**Purpose**: Show which AGV is executing which path.

**Requirements**:
1. Fetch active orders
2. For each active order, highlight the path on the map
3. Use different colors for different orders
4. Show AGV position along the path

**Functionality checklist**:
- [ ] Fetch orders with status ACTIVE or SENT
- [ ] For each order, extract nodes array
- [ ] Highlight edges between those nodes (thicker line, different color)
- [ ] Show progress (which node AGV is at)
- [ ] Legend showing order colors

**UI sketch**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Fleet Map - Active Orders              [Legend: Show/Hide]     │
├─────────────────────────────────────────────────────────────────┤
│ Legend:                                                         │
│ 🟦 ORD_A3F2B8C1 (AGV_01): Node_B → Node_A → Node_C            │
│ 🟧 ORD_B7E1F3D2 (AGV_02): Node_D → Node_E → Node_F            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│         ○ Node_A ════ ○ Node_B ──── ○ Node_C                   │
│                     🟦    🟦🟢                                  │
│                         AGV_01                                  │
│                                                                 │
│         ○ Node_D ════ ○ Node_E ════ ○ Node_F                   │
│                     🟧    🟧🟢                                  │
│                         AGV_02                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### **Phase 4: AGV Control (MISSING BACKEND API)**

Operators need to pause, resume, and cancel AGVs.

**⚠️ BLOCKER**: Backend does not expose REST API for instant actions.

#### **Task 4.1: Add Backend Endpoints (Django work required)**

**File**: `/agv-system/backend/vda5050/views.py`

Add these endpoints to AGVViewSet:

```python
@action(detail=True, methods=['post'])
def pause(self, request, serial_number=None):
    """Pause AGV (send startPause instant action)"""
    agv = self.get_object()
    action = InstantAction.objects.create(
        agv=agv,
        action_type='startPause',
        created_by=request.user if request.user.is_authenticated else None
    )
    return Response({'success': True, 'action_id': action.action_id})

@action(detail=True, methods=['post'])
def resume(self, request, serial_number=None):
    """Resume AGV (send stopPause instant action)"""
    agv = self.get_object()
    action = InstantAction.objects.create(
        agv=agv,
        action_type='stopPause',
        created_by=request.user if request.user.is_authenticated else None
    )
    return Response({'success': True, 'action_id': action.action_id})

@action(detail=True, methods=['post'])
def cancel_order(self, request, serial_number=None):
    """Cancel current order (send cancelOrder instant action)"""
    agv = self.get_object()
    action = InstantAction.objects.create(
        agv=agv,
        action_type='cancelOrder',
        created_by=request.user if request.user.is_authenticated else None
    )
    return Response({'success': True, 'action_id': action.action_id})
```

**New endpoints**:
- `POST /api/agvs/{serial_number}/pause/`
- `POST /api/agvs/{serial_number}/resume/`
- `POST /api/agvs/{serial_number}/cancel_order/`

---

#### **Task 4.2: Add Frontend API Functions**
File: `/agv-gui/src/lib/api.ts`

```typescript
// Pause AGV
export async function pauseAgv(serialNumber: string): Promise<{success: boolean, action_id: string}> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/pause/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  
  if (!response.ok) {
    throw new Error(`Failed to pause AGV: ${response.statusText}`)
  }
  
  return response.json()
}

// Resume AGV
export async function resumeAgv(serialNumber: string): Promise<{success: boolean, action_id: string}> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/resume/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  
  if (!response.ok) {
    throw new Error(`Failed to resume AGV: ${response.statusText}`)
  }
  
  return response.json()
}

// Cancel AGV order
export async function cancelAgvOrder(serialNumber: string): Promise<{success: boolean, action_id: string}> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/cancel_order/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  
  if (!response.ok) {
    throw new Error(`Failed to cancel order: ${response.statusText}`)
  }
  
  return response.json()
}
```

---

#### **Task 4.3: Add Control Buttons to Fleet Dashboard**
File: `/agv-gui/src/app/fleet/page.tsx`

Add buttons to each AGV card:
- **Pause** button (if driving)
- **Resume** button (if paused)
- **Cancel Order** button (if has active order)

**Functionality checklist**:
- [ ] Show "Pause" button only if AGV is driving
- [ ] Show "Resume" button only if AGV is paused
- [ ] Show "Cancel Order" button only if AGV has active order
- [ ] Call API on button click
- [ ] Show success/error toast notification
- [ ] Refresh AGV state after action

**UI sketch**:
```
┌────────────────┐
│ AGV_01         │
│ 🟢 ONLINE      │
│ ████████░░ 85% │
│ 🚚 Driving     │
│ Order: ORD_... │
│                │
│ [Pause]  [Cancel Order]
└────────────────┘
```

---

### **Phase 5: Algorithm Verification Tools (NICE TO HAVE)**

Help operators understand and verify the bidding algorithm.

#### **Task 5.1: Create Bidding Preview Endpoint (Backend)**

**⚠️ BLOCKER**: Backend does not expose bid details.

**File**: `/agv-system/backend/vda5050/views.py`

Add to TaskViewSet:

```python
@action(detail=False, methods=['post'])
def preview(self, request):
    """Preview auction results without creating order"""
    pickup = request.data.get('pickup_node_id')
    delivery = request.data.get('delivery_node_id')
    
    # Run auction but don't create order
    result = self.bidding_engine.run_auction(pickup, delivery)
    
    # Return all bids for display
    return Response({
        'winner': result['winner'],
        'all_bids': result.get('all_bids', []),  # Need to modify engine to return this
        'winner_score': result.get('winner_score'),
        'pickup_node': pickup,
        'delivery_node': delivery
    })
```

**New endpoint**: `POST /api/tasks/preview/`

**Backend modification required**: Modify `BiddingEngine` and `AuctionCoordinator` to return all bids, not just the winner.

---

#### **Task 5.2: Create Bidding Comparison Page**
File: `/agv-gui/src/app/tasks/preview/page.tsx`

**Purpose**: Show operators which AGV would win for a given task and why.

**Requirements**:
1. Same interface as task creation (pickup/delivery dropdowns)
2. "Preview Auction" button
3. Display all AGVs and their bid scores
4. Highlight winner
5. Show breakdown:
   - Current position
   - Distance to pickup
   - Distance to delivery
   - Energy cost
   - Time cost
   - Battery level
   - Wait time (if busy)

**Functionality checklist**:
- [ ] Call `previewTask()` API
- [ ] Display all bids in a table
- [ ] Sort by score (lowest = winner)
- [ ] Highlight winner row
- [ ] Show detailed cost breakdown
- [ ] Show path for winner

**UI sketch**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Auction Preview                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Pickup Node:  [Node_A ▼]                                       │
│ Delivery Node: [Node_C ▼]                                      │
│                                                                 │
│ [Preview Auction]                                               │
│                                                                 │
│ ─── Bidding Results ───                                         │
│ AGV      Position  Battery  Energy  Time  Wait  Score  Winner  │
│ AGV_01   Node_B    85%      25.5kJ  8.0s  0s    2.07   ✅      │
│ AGV_02   Node_E    90%      25.5kJ  11.0s 3s    2.45           │
│ AGV_03   Node_H    65%      42.0kJ  15.0s 0s    3.63           │
│                                                                 │
│ Winner: AGV_01                                                  │
│ Path: Node_B → Node_A (pickup) → Node_C (delivery)            │
│ Total Distance: 3 edges                                         │
│ Total Time: 8.0 seconds                                         │
│ Energy Consumption: 25.5 kJ                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

### **Phase 6: Testing & Validation (CRITICAL)**

Before deploying, operators need to verify the system works end-to-end.

#### **Task 6.1: Create System Test Page**
File: `/agv-gui/src/app/test/page.tsx`

**Purpose**: One-click system verification.

**Requirements**:
1. Check backend connectivity
2. Check MQTT broker (indirectly via AGV online status)
3. Check graph is loaded (nodes, edges)
4. Check AGVs are registered
5. Run a test task assignment
6. Verify order status changes

**Functionality checklist**:
- [ ] Test: Fetch AGVs (should return array)
- [ ] Test: Fetch graph nodes (should return array)
- [ ] Test: Fetch orders (should return array)
- [ ] Test: Count online AGVs (need at least 1)
- [ ] Test: Create dummy task (Node_A → Node_B)
- [ ] Test: Verify order was created
- [ ] Display all results with ✅ or ❌

**UI sketch**:
```
┌─────────────────────────────────────────┐
│ System Health Check                     │
├─────────────────────────────────────────┤
│ ✅ Backend API: Connected               │
│ ✅ Graph loaded: 8 nodes, 20 edges      │
│ ✅ AGVs registered: 7 total             │
│ ✅ AGVs online: 5 online                │
│ ✅ Orders table: Accessible             │
│ ✅ Test task: Created (ORD_TEST123)     │
│ ✅ Order status: SENT                   │
│                                         │
│ System Status: 🟢 ALL SYSTEMS GO        │
│                                         │
│ [Run Test Again]                        │
└─────────────────────────────────────────┘
```

---

#### **Task 6.2: Integration with AGV Simulators**

**Documentation needed**: Create a guide for operators.

**File**: `/agv-gui/docs/TESTING_GUIDE.md`

**Content**:
1. How to start AGV simulators (`python tests/simulators/multi_mock_agv.py`)
2. How to verify simulators are connected (check Fleet Dashboard)
3. How to create test tasks
4. How to monitor task execution
5. How to interpret auction results
6. Common troubleshooting steps

---

## 📊 Implementation Summary Table

| Phase | Task | Priority | Backend Required | Estimated Time |
|-------|------|----------|------------------|----------------|
| **1** | Extend API Client | 🔴 Critical | ✅ Already exists | 1 hour |
| **1** | Task Creation Page | 🔴 Critical | ✅ Already exists | 2 hours |
| **1** | Order Tracking Page | 🔴 Critical | ✅ Already exists | 2 hours |
| **1** | Order Details Modal | 🔴 Critical | ✅ Already exists | 1 hour |
| **2** | Fleet Dashboard | 🔴 Critical | ✅ Already exists | 3 hours |
| **2** | AGV Details Modal | 🔴 Critical | ✅ Already exists | 1 hour |
| **3** | Fleet Map Visualization | 🟡 High | ✅ Already exists | 4 hours |
| **3** | Highlight Active Paths | 🟡 High | ✅ Already exists | 2 hours |
| **4** | Backend: Instant Actions | 🔴 Critical | ⚠️ **MISSING** | 1 hour |
| **4** | Frontend: Control Buttons | 🔴 Critical | ⚠️ Needs Phase 4.1 | 1 hour |
| **5** | Backend: Bidding Preview | 🟢 Nice to have | ⚠️ **MISSING** | 2 hours |
| **5** | Frontend: Bidding Preview | 🟢 Nice to have | ⚠️ Needs Phase 5.1 | 2 hours |
| **6** | System Test Page | 🟡 High | ✅ Already exists | 2 hours |
| **6** | Testing Documentation | 🟡 High | ✅ N/A | 1 hour |

**Total Estimated Time (without Phase 5)**: ~20 hours
**Total Estimated Time (complete)**: ~24 hours

---

## 🎯 Minimum Viable Product (MVP)

To verify the core auction-based task assignment system, implement:

**MUST HAVE**:
1. ✅ Phase 1: Task Assignment (Tasks 1.1 - 1.4)
2. ✅ Phase 2: Fleet Monitoring (Tasks 2.1 - 2.2)
3. ✅ Phase 4.1 - 4.3: AGV Control (requires backend work)

**SHOULD HAVE**:
4. ✅ Phase 3: Fleet Map (Tasks 3.1 - 3.2)
5. ✅ Phase 6.1: System Test Page

**NICE TO HAVE**:
6. ⏳ Phase 5: Bidding Preview (requires backend extension)

---

## 🚀 Quick Start Guide for Implementation

### Step 1: Setup Test Environment
```bash
# Terminal 1: Start backend
cd agv-system
docker-compose up -d

# Terminal 2: Setup test data
docker-compose exec web python manage.py setup_test_agvs --count 7
docker-compose exec web python manage.py setup_test_graph

# Terminal 3: Start simulators
cd tests/simulators
python multi_mock_agv.py

# Terminal 4: Start frontend
cd ../../agv-gui
pnpm dev
```

### Step 2: Implement in Order
1. Phase 1 (Task Assignment) - 6 hours
2. Phase 2 (Fleet Monitoring) - 4 hours
3. Phase 4.1 (Backend Instant Actions) - 1 hour
4. Phase 4.2-4.3 (Frontend Control) - 2 hours
5. Phase 3 (Fleet Map) - 6 hours
6. Phase 6 (Testing) - 3 hours

### Step 3: Verification
After each phase, verify:
- [ ] Code builds without errors (`pnpm build`)
- [ ] TypeScript types are correct (`pnpm typecheck`)
- [ ] API calls work (test in browser)
- [ ] Simulators respond to actions
- [ ] No console errors

---

## 🎓 Success Criteria

**MVP is complete when**:
1. ✅ Operator can create transport task (pickup → delivery)
2. ✅ System runs auction and assigns task to best AGV
3. ✅ Operator can see auction winner and path
4. ✅ Operator can monitor AGV fleet status (battery, position, online/offline)
5. ✅ Operator can see active orders and their status
6. ✅ Operator can pause, resume, cancel AGVs
7. ✅ Operator can see AGVs on map in real-time
8. ✅ System health check passes

**Algorithm verification complete when**:
1. ✅ Bidding system considers battery levels
2. ✅ Bidding system considers current AGV position
3. ✅ Bidding system considers active tasks (wait cost)
4. ✅ Closest idle AGV with sufficient battery wins
5. ✅ Busy AGVs have higher cost (wait time penalty)
6. ✅ Load balancing distributes tasks across fleet

---

## 📌 Notes for Development

### Auto-Refresh Strategy
- **Fleet Dashboard**: 3-5 seconds (battery, position changes slowly)
- **Order Tracking**: 5 seconds (status changes are not instant)
- **Fleet Map**: 2 seconds (position updates for smooth movement)

### Error Handling
- All API calls must have try-catch
- Display user-friendly error messages
- Log errors to console for debugging
- Show toast notifications for success/error

### Data Polling vs WebSocket
- **Current**: Use `setInterval` for polling
- **Future**: WebSocket for true real-time updates (not critical for MVP)

### Testing Approach
- Use AGV simulators (`multi_mock_agv.py`) for all testing
- Create at least 3 test tasks
- Verify status changes: CREATED → SENT → ACTIVE → COMPLETED
- Verify battery drain during task execution

---

## 🔧 Backend Work Required Summary

**CRITICAL** (blocks Phase 4):
1. Add `/api/agvs/{serial}/pause/` endpoint
2. Add `/api/agvs/{serial}/resume/` endpoint
3. Add `/api/agvs/{serial}/cancel_order/` endpoint

**OPTIONAL** (blocks Phase 5):
4. Add `/api/tasks/preview/` endpoint
5. Modify `BiddingEngine` to return all bids (not just winner)

**Recommendation**: Implement Phase 4 endpoints first. They are critical for operator control.

---

**This plan focuses on FUNCTIONALITY over appearance. Implement features in order. Test each phase before moving to the next. The goal is a working system that operators can use to verify the auction-based task allocation algorithm.**

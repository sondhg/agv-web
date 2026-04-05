# Phase 1, Task 1.2: Task Creation Page - Testing Guide

## ✅ What Was Created

**New Page**: `/tasks/create`  
**File**: `/src/app/tasks/create/page.tsx`

### Features Implemented

1. **Node Selection**
   - Dropdown to select pickup node
   - Dropdown to select delivery node
   - Auto-loads available nodes from backend
   - Shows node descriptions (if available)

2. **Validation**
   - Ensures pickup and delivery nodes are selected
   - Prevents selecting same node for both
   - Shows clear error messages

3. **Auction Execution**
   - "Create Transport Task" button triggers auction
   - Shows loading state while auction runs
   - Displays detailed results

4. **Result Display**
   - Winner AGV serial number
   - Order ID (for tracking)
   - Order status (CREATED/QUEUED)
   - Pickup and delivery nodes confirmation
   - **Calculated path visualization** (shows route with arrows)
   - Total waypoints count

5. **Error Handling**
   - Network errors
   - Backend errors (no AGVs available, no path found)
   - User-friendly error messages

---

## 🧪 Testing Instructions

### Step 1: Start the Frontend

```bash
cd agv-gui
pnpm dev
```

The dev server should start at `http://localhost:5173`

### Step 2: Navigate to Task Creation Page

Open your browser and go to:
```
http://localhost:5173/tasks/create
```

You should see the "Create Transport Task" page.

---

## 📝 Test Cases

### Test Case 1: Create a Simple Task

**Steps**:
1. Open `http://localhost:5173/tasks/create`
2. Select **Pickup Node**: `Node_A`
3. Select **Delivery Node**: `Node_C`
4. Click "Create Transport Task"

**Expected Result**:
- ✅ Loading state shows "Running Auction..."
- ✅ After ~1 second, success message appears
- ✅ Shows winner AGV (e.g., "AGV_04" since it's at Node_A)
- ✅ Shows order ID (e.g., "ORD_...")
- ✅ Shows status: "CREATED" or "QUEUED"
- ✅ Shows path with arrows (e.g., `Node_A → Node_C`)

**Screenshot Area**: The green success box should show:
```
✓ Task Assigned Successfully
  Order sent to AGV

  Winner AGV: AGV_04
  Order ID: ORD_...
  Status: CREATED
  Pickup: Node_A
  Delivery: Node_C

  Calculated Path:
  Node_A → Node_C
  Total waypoints: 2
```

---

### Test Case 2: Create a Task Requiring Multi-Hop Path

**Steps**:
1. Reload the page (to clear previous result)
2. Select **Pickup Node**: `Node_A`
3. Select **Delivery Node**: `Node_H`
4. Click "Create Transport Task"

**Expected Result**:
- ✅ Success message appears
- ✅ Path shows multiple hops (e.g., `Node_B → Node_A → Node_E → Node_H` or similar)
- ✅ Winner AGV is selected based on proximity and battery
- ✅ Total waypoints > 2

**Why this works**: The backend uses NetworkX to find the shortest path between any two nodes.

---

### Test Case 3: Validation - Same Node

**Steps**:
1. Select **Pickup Node**: `Node_B`
2. Select **Delivery Node**: `Node_B` (same node)
3. Click "Create Transport Task"

**Expected Result**:
- ✅ Red error message: "Pickup and delivery nodes must be different"
- ✅ No task is created
- ✅ Error clears when you change selection

---

### Test Case 4: Multiple Tasks (Load Balancing)

**Steps**:
1. Create task: `Node_A` → `Node_C` (wait for success)
2. Reload page
3. Create task: `Node_E` → `Node_H` (wait for success)
4. Reload page
5. Create task: `Node_B` → `Node_F` (wait for success)

**Expected Result**:
- ✅ Each task succeeds
- ✅ Different AGVs win (load balancing in action!)
- ✅ AGVs closer to pickup node are preferred
- ✅ Busy AGVs have lower priority (wait cost)

**Verification**: Check simulator output to see different AGVs receiving orders.

---

### Test Case 5: No AGVs Online (Error Handling)

**Steps**:
1. Stop the AGV simulators (Ctrl+C in the simulator terminal)
2. Wait 10 seconds for AGVs to go offline
3. Try to create a task

**Expected Result**:
- ✅ Red error message: "No suitable AGV found"
- ✅ Shows clear error from backend
- ✅ No order is created

**Recovery**:
1. Restart simulators: `python multi_mock_agv.py`
2. Wait 10 seconds
3. Try creating task again - should work

---

## 🔍 What to Observe

### In the Browser
- **Loading States**: Button shows spinner during auction
- **Success Display**: Green alert box with all details
- **Error Display**: Red alert box with clear message
- **Path Visualization**: Arrow icons between nodes
- **Responsive Layout**: Works on different screen sizes

### In the Simulator Terminal
After creating a task, you should see:
```
📦 AGV_04: Order received: ORD_...
📍 AGV_04: Executing nodes: ['Node_A', 'Node_C']
🚚 AGV_04: Moving Node_A → Node_C (Battery: 79.5%)
✅ AGV_04: Completed order ORD_...
```

### In Backend Logs (Optional)
```bash
cd agv-system
docker-compose logs -f web
```

You should see auction bidding logs showing which AGVs bid and who won.

---

## ✅ Success Criteria Checklist

Before moving to the next task, confirm:

- [ ] Page loads without errors at `/tasks/create`
- [ ] Dropdowns show all 8 nodes (Node_A through Node_H)
- [ ] Can select different pickup and delivery nodes
- [ ] "Create Transport Task" button is enabled only when both nodes selected
- [ ] Task creation triggers auction successfully
- [ ] Winner AGV is displayed
- [ ] Order ID is generated
- [ ] Path is shown with arrow visualization
- [ ] Can create multiple tasks in succession
- [ ] Validation prevents same node selection
- [ ] Error handling works when no AGVs available

---

## 🐛 Troubleshooting

### Issue: "Failed to load graph nodes"
**Fix**: Make sure graph is setup:
```bash
cd agv-system
docker-compose exec web python manage.py setup_test_graph
```

### Issue: "No suitable AGV found"
**Fix**: Start simulators:
```bash
cd agv-system/tests/simulators
python multi_mock_agv.py
```

### Issue: Page shows 404 Not Found
**Fix**: Make sure frontend dev server is running:
```bash
cd agv-gui
pnpm dev
```

### Issue: Dropdowns are empty
**Fix**: Check browser console for errors. Backend must be running.

---

## 📸 Expected UI Appearance

```
┌──────────────────────────────────────────────────────┐
│ Create Transport Task                                │
│ Assign a pickup and delivery task to the AGV fleet. │
│ The system will automatically select the best AGV... │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Pickup Node                                          │
│ [Select pickup location ▼]                          │
│ The location where the AGV will pick up the load    │
│                                                      │
│ Delivery Node                                        │
│ [Select delivery location ▼]                        │
│ The destination where the AGV will deliver...       │
│                                                      │
│ [  Create Transport Task  ]                         │
│                                                      │
├──────────────────────────────────────────────────────┤
│ ✓ Task Assigned Successfully                        │
│   Order sent to AGV                                  │
│                                                      │
│   Winner AGV: AGV_04                                 │
│   Order ID: ORD_B04D2185                            │
│   Status: CREATED                                    │
│   Pickup: Node_A                                     │
│   Delivery: Node_C                                   │
│                                                      │
│   Calculated Path:                                   │
│   [Node_A] → [Node_C]                               │
│   Total waypoints: 2                                 │
└──────────────────────────────────────────────────────┘
```

---

## 📋 Next Steps

Once you confirm the page works correctly, we'll proceed to:

**Phase 1, Task 1.3**: Order Tracking Page

This will let you see all created orders and monitor their status (CREATED → SENT → ACTIVE → COMPLETED).

---

## 💡 Notes

- The page uses real-time data from your backend
- Auction results match the bidding algorithm logs
- Path is calculated using NetworkX shortest path
- AGV selection considers: distance, battery, active tasks
- You can create tasks faster than AGVs can complete them (queueing works)

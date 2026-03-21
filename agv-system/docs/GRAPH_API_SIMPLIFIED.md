# Graph API - Simplified Field Requirements

## Mandatory Fields

### Nodes
**Required fields only:**
- `node_id` (string) - Unique identifier
- `map_id` (string) - Map identifier
- `x` (float) - X coordinate
- `y` (float) - Y coordinate

**Optional fields (with defaults):**
- `theta` (float) - Orientation angle, default: 0.0
- `description` (string) - Description, default: ""

### Edges
**Required fields only:**
- `start_node_id` (string) - Starting node ID
- `end_node_id` (string) - Ending node ID
- `map_id` (string) - Map identifier

**Optional fields (with defaults/auto-calculation):**
- `length` (float) - **Auto-calculated** from node coordinates (Euclidean distance)
- `max_velocity` (float) - Maximum velocity, default: 1.0 m/s
- `is_directed` (boolean) - Direction flag, default: true (one-way)

---

## Examples

### Create a Node (Minimal)
```bash
curl -X POST http://localhost:8000/api/graph/nodes/ \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "Node_A",
    "map_id": "warehouse_1",
    "x": 0.0,
    "y": 0.0
  }'
```

**Response:**
```json
{
  "id": 1,
  "node_id": "Node_A",
  "map_id": "warehouse_1",
  "x": 0.0,
  "y": 0.0,
  "theta": 0.0,
  "description": ""
}
```

### Create a Node (With Optional Fields)
```bash
curl -X POST http://localhost:8000/api/graph/nodes/ \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "Node_B",
    "map_id": "warehouse_1",
    "x": 10.0,
    "y": 0.0,
    "theta": 90.0,
    "description": "Loading dock"
  }'
```

### Create an Edge (Minimal - Auto-calculated Length)
```bash
curl -X POST http://localhost:8000/api/graph/edges/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_node_id": "Node_A",
    "end_node_id": "Node_B",
    "map_id": "warehouse_1"
  }'
```

**Response:**
```json
{
  "id": 1,
  "start_node": {
    "id": 1,
    "node_id": "Node_A",
    "map_id": "warehouse_1",
    "x": 0.0,
    "y": 0.0,
    "theta": 0.0,
    "description": ""
  },
  "end_node": {
    "id": 2,
    "node_id": "Node_B",
    "map_id": "warehouse_1",
    "x": 10.0,
    "y": 0.0,
    "theta": 90.0,
    "description": "Loading dock"
  },
  "map_id": "warehouse_1",
  "length": 10.0,
  "max_velocity": 1.0,
  "is_directed": true
}
```

**Note:** The `length` was automatically calculated as the Euclidean distance between (0, 0) and (10, 0) = 10.0 meters.

### Create an Edge (With Optional Fields)
```bash
curl -X POST http://localhost:8000/api/graph/edges/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_node_id": "Node_B",
    "end_node_id": "Node_A",
    "map_id": "warehouse_1",
    "max_velocity": 2.5,
    "is_directed": false
  }'
```

**Response:**
```json
{
  "id": 2,
  "start_node": {...},
  "end_node": {...},
  "map_id": "warehouse_1",
  "length": 10.0,
  "max_velocity": 2.5,
  "is_directed": false
}
```

---

## Bulk Creation Examples

### Bulk Create Nodes (Minimal)
```bash
curl -X POST http://localhost:8000/api/graph/nodes/bulk_create/ \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [
      {"node_id": "N1", "map_id": "map1", "x": 0, "y": 0},
      {"node_id": "N2", "map_id": "map1", "x": 10, "y": 0},
      {"node_id": "N3", "map_id": "map1", "x": 10, "y": 10}
    ]
  }'
```

### Bulk Create Edges (Minimal - Auto-calculated Lengths)
```bash
curl -X POST http://localhost:8000/api/graph/edges/bulk_create/ \
  -H "Content-Type: application/json" \
  -d '{
    "edges": [
      {"start_node_id": "N1", "end_node_id": "N2", "map_id": "map1"},
      {"start_node_id": "N2", "end_node_id": "N3", "map_id": "map1"},
      {"start_node_id": "N3", "end_node_id": "N1", "map_id": "map1"}
    ]
  }'
```

**Response:**
```json
{
  "message": "Successfully created 3 edges",
  "edges": [
    {
      "id": 1,
      "start_node": {...},
      "end_node": {...},
      "map_id": "map1",
      "length": 10.0,
      "max_velocity": 1.0,
      "is_directed": true
    },
    {
      "id": 2,
      "start_node": {...},
      "end_node": {...},
      "map_id": "map1",
      "length": 10.0,
      "max_velocity": 1.0,
      "is_directed": true
    },
    {
      "id": 3,
      "start_node": {...},
      "end_node": {...},
      "map_id": "map1",
      "length": 14.142135623730951,
      "max_velocity": 1.0,
      "is_directed": true
    }
  ]
}
```

**Note:** All lengths were auto-calculated:
- N1 → N2: 10.0 (horizontal distance)
- N2 → N3: 10.0 (vertical distance)
- N3 → N1: 14.14 (diagonal distance, √(10² + 10²))

---

## ReactFlow Integration

### Create Node from ReactFlow
```typescript
const createNode = async (position: { x: number; y: number }, nodeId: string) => {
  const response = await fetch('http://localhost:8000/api/graph/nodes/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      node_id: nodeId,
      map_id: 'warehouse_1',
      x: position.x,
      y: position.y
      // theta and description are optional
    })
  })
  return await response.json()
}
```

### Create Edge from ReactFlow
```typescript
const createEdge = async (source: string, target: string) => {
  const response = await fetch('http://localhost:8000/api/graph/edges/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_node_id: source,
      end_node_id: target,
      map_id: 'warehouse_1'
      // length is auto-calculated
      // max_velocity defaults to 1.0
      // is_directed defaults to true
    })
  })
  return await response.json()
}
```

---

## Length Calculation

The edge `length` is automatically calculated using the **Euclidean distance formula**:

```
length = √((x₂ - x₁)² + (y₂ - y₁)²)
```

Where:
- (x₁, y₁) = coordinates of start_node
- (x₂, y₂) = coordinates of end_node

### Examples:
| Start Node | End Node | Calculation | Length |
|------------|----------|-------------|--------|
| (0, 0) | (10, 0) | √((10-0)² + (0-0)²) = √100 | 10.0 |
| (0, 0) | (0, 10) | √((0-0)² + (10-0)²) = √100 | 10.0 |
| (0, 0) | (10, 10) | √((10-0)² + (10-0)²) = √200 | 14.14 |
| (0, 0) | (50, 100) | √((50-0)² + (100-0)²) = √12500 | 111.80 |

---

## Summary

✅ **Nodes**: Only 4 mandatory fields (node_id, map_id, x, y)  
✅ **Edges**: Only 3 mandatory fields (start_node_id, end_node_id, map_id)  
✅ **Auto-calculation**: Edge length is automatically computed from node coordinates  
✅ **Defaults**: Optional fields have sensible defaults (theta=0, description="", max_velocity=1.0, is_directed=true)  
✅ **Bulk Operations**: Support for creating multiple nodes/edges with minimal data

This makes the API very easy to use from ReactFlow - just send node positions and connections!

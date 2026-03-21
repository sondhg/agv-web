# Graph API Quick Reference

Quick reference for the most commonly used Graph Management API endpoints.

## 🔗 Base URL
```
http://localhost:8000/api/graph/
```

---

## 📍 Nodes

### Get All Nodes
```bash
GET /api/graph/nodes/
GET /api/graph/nodes/?map_id=default_map
```

### Create Node
```bash
POST /api/graph/nodes/
{
  "node_id": "Node_X",
  "map_id": "default_map",
  "x": 15.5,
  "y": 20.0,
  "theta": 0.0,
  "description": "Charging station"
}
```

### Update Node
```bash
PATCH /api/graph/nodes/{id}/
{
  "description": "Updated description",
  "x": 16.0
}
```

### Delete Node
```bash
DELETE /api/graph/nodes/{id}/
```
⚠️ **Note**: Cannot delete if node has connected edges

### Bulk Create Nodes
```bash
POST /api/graph/nodes/bulk_create/
{
  "nodes": [
    {"node_id": "N1", "x": 0, "y": 0, "map_id": "map1"},
    {"node_id": "N2", "x": 10, "y": 0, "map_id": "map1"}
  ]
}
```

---

## 🔗 Edges

### Get All Edges
```bash
GET /api/graph/edges/
GET /api/graph/edges/?map_id=default_map
GET /api/graph/edges/?node_id=Node_A
```

### Create Edge
```bash
POST /api/graph/edges/
{
  "start_node_id": "Node_A",
  "end_node_id": "Node_B",
  "map_id": "default_map",
  "max_velocity": 2.0,
  "is_directed": true
}
```
💡 **Tip**: `length` is auto-calculated if not provided

### Create Edge with Manual Length
```bash
POST /api/graph/edges/
{
  "start_node_id": "Node_A",
  "end_node_id": "Node_B",
  "map_id": "default_map",
  "length": 15.0,
  "max_velocity": 2.0,
  "is_directed": false
}
```

### Update Edge
```bash
PATCH /api/graph/edges/{id}/
{
  "max_velocity": 3.0
}
```

### Delete Edge
```bash
DELETE /api/graph/edges/{id}/
```

### Bulk Create Edges
```bash
POST /api/graph/edges/bulk_create/
{
  "edges": [
    {
      "start_node_id": "N1",
      "end_node_id": "N2",
      "map_id": "map1",
      "max_velocity": 2.0,
      "is_directed": true
    }
  ]
}
```

---

## 📊 Statistics & Validation

### Node Statistics
```bash
GET /api/graph/nodes/statistics/

# Response:
{
  "total_nodes": 8,
  "maps": ["default_map"],
  "nodes_per_map": {"default_map": 8}
}
```

### Edge Statistics
```bash
GET /api/graph/edges/statistics/

# Response:
{
  "total_edges": 20,
  "directed_edges": 20,
  "bidirectional_edges": 0,
  "average_length": 10.0,
  "average_max_velocity": 2.0
}
```

### Validate Graph
```bash
GET /api/graph/validate/

# Response:
{
  "valid": true,
  "issues": [],
  "warnings": ["Node X is isolated (no connections)"],
  "total_nodes": 8,
  "total_edges": 20
}
```

---

## 💾 Import/Export

### Export Graph
```bash
GET /api/graph/export/
GET /api/graph/export/?map_id=default_map

# Response:
{
  "map_id": "default_map",
  "nodes": [...],
  "edges": [...],
  "metadata": {
    "total_nodes": 8,
    "total_edges": 20,
    "exported_at": "2024-03-21T10:30:00Z"
  }
}
```

### Import Graph
```bash
POST /api/graph/import/
{
  "clear_existing": false,
  "nodes": [...],
  "edges": [...]
}

# Response:
{
  "message": "Import completed: 8 nodes, 20 edges",
  "created_nodes": 8,
  "created_edges": 20,
  "errors": []
}
```

---

## 🎨 ReactFlow Integration

### Fetch Graph for ReactFlow
```typescript
const response = await Promise.all([
  fetch('http://localhost:8000/api/graph/nodes/'),
  fetch('http://localhost:8000/api/graph/edges/')
])
const [nodes, edges] = await Promise.all(response.map(r => r.json()))
```

### Transform to ReactFlow Format
```typescript
// Nodes
const reactFlowNodes = nodes.map(node => ({
  id: node.node_id,
  position: { x: node.x, y: node.y },
  data: { label: node.node_id }
}))

// Edges
const reactFlowEdges = edges.map(edge => ({
  id: edge.id.toString(),
  source: edge.start_node.node_id,
  target: edge.end_node.node_id,
  label: `${edge.length}m`
}))
```

### Save Node from ReactFlow
```typescript
const saveNode = async (node) => {
  await fetch('http://localhost:8000/api/graph/nodes/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      node_id: node.id,
      map_id: 'default_map',
      x: node.position.x,
      y: node.position.y,
      theta: 0,
      description: node.data.label
    })
  })
}
```

### Save Edge from ReactFlow
```typescript
const saveEdge = async (connection) => {
  await fetch('http://localhost:8000/api/graph/edges/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_node_id: connection.source,
      end_node_id: connection.target,
      map_id: 'default_map',
      max_velocity: 2.0,
      is_directed: true
    })
  })
}
```

---

## ⚠️ Common Error Responses

### Node Already Exists
```json
{
  "node_id": ["Node with node_id 'Node_A' already exists."]
}
```

### Node Not Found (for Edge Creation)
```json
{
  "non_field_errors": ["Node not found: Node_X"]
}
```

### Cannot Delete Node with Edges
```json
{
  "error": "Cannot delete node Node_A. It is connected to 4 edge(s). Delete the edges first."
}
```

### Invalid Coordinates
```json
{
  "x": ["X coordinate must be between -1000 and 1000"]
}
```

---

## 🔑 Field Descriptions

### Node Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | read-only | Auto-generated ID |
| `node_id` | string | ✅ | Unique identifier (e.g., "Node_A") |
| `map_id` | string | ✅ | Map identifier (e.g., "default_map") |
| `x` | float | ✅ | X coordinate (-1000 to 1000) |
| `y` | float | ✅ | Y coordinate (-1000 to 1000) |
| `theta` | float | optional | Orientation angle (-180° to 180°), default: 0 |
| `description` | string | optional | Human-readable description |

### Edge Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | read-only | Auto-generated ID |
| `start_node_id` | string | ✅ (write) | ID of starting node |
| `end_node_id` | string | ✅ (write) | ID of ending node |
| `start_node` | object | read-only | Full start node object |
| `end_node` | object | read-only | Full end node object |
| `map_id` | string | ✅ | Map identifier |
| `length` | float | optional | Edge length (auto-calculated if omitted) |
| `max_velocity` | float | optional | Max velocity (m/s), default: 1.0 |
| `is_directed` | boolean | optional | Direction (true = one-way), default: true |

---

## 🚀 Quick Test Commands

### Test Complete Workflow
```bash
# 1. Create two nodes
curl -X POST http://localhost:8000/api/graph/nodes/ \
  -H "Content-Type: application/json" \
  -d '{"node_id": "A", "x": 0, "y": 0, "map_id": "test"}'

curl -X POST http://localhost:8000/api/graph/nodes/ \
  -H "Content-Type: application/json" \
  -d '{"node_id": "B", "x": 10, "y": 10, "map_id": "test"}'

# 2. Create edge between them
curl -X POST http://localhost:8000/api/graph/edges/ \
  -H "Content-Type: application/json" \
  -d '{"start_node_id": "A", "end_node_id": "B", "map_id": "test", "max_velocity": 2.0}'

# 3. List all nodes and edges
curl http://localhost:8000/api/graph/nodes/
curl http://localhost:8000/api/graph/edges/

# 4. Validate graph
curl http://localhost:8000/api/graph/validate/

# 5. Export graph
curl http://localhost:8000/api/graph/export/ > graph.json
```

---

For detailed documentation, see `/docs/GRAPH_API.md`

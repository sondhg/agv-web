# Graph Management API Documentation

This document describes the REST API endpoints for managing graph nodes and edges in the AGV system.

## Base URL

```
http://localhost:8000/api/
```

---

## Graph Nodes API

### List All Nodes

**Endpoint:** `GET /api/graph/nodes/`

**Query Parameters:**
- `map_id` (optional): Filter nodes by map ID

**Example Request:**
```bash
curl http://localhost:8000/api/graph/nodes/
curl http://localhost:8000/api/graph/nodes/?map_id=default_map
```

**Example Response:**
```json
[
  {
    "id": 1,
    "node_id": "Node_A",
    "map_id": "default_map",
    "x": 0.0,
    "y": 0.0,
    "theta": 0.0,
    "description": "Warehouse entrance"
  },
  {
    "id": 2,
    "node_id": "Node_B",
    "map_id": "default_map",
    "x": 10.0,
    "y": 0.0,
    "theta": 0.0,
    "description": "Loading dock"
  }
]
```

---

### Create a Node

**Endpoint:** `POST /api/graph/nodes/`

**Request Body:**
```json
{
  "node_id": "Node_X",
  "map_id": "default_map",
  "x": 15.5,
  "y": 20.0,
  "theta": 0.0,
  "description": "Charging station"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/graph/nodes/ \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "Node_X",
    "map_id": "default_map",
    "x": 15.5,
    "y": 20.0,
    "theta": 0.0,
    "description": "Charging station"
  }'
```

**Example Response:**
```json
{
  "id": 10,
  "node_id": "Node_X",
  "map_id": "default_map",
  "x": 15.5,
  "y": 20.0,
  "theta": 0.0,
  "description": "Charging station"
}
```

---

### Get a Specific Node

**Endpoint:** `GET /api/graph/nodes/{id}/`

**Example Request:**
```bash
curl http://localhost:8000/api/graph/nodes/1/
```

---

### Update a Node

**Endpoint:** `PUT /api/graph/nodes/{id}/` (full update)  
**Endpoint:** `PATCH /api/graph/nodes/{id}/` (partial update)

**Example Request (Partial Update):**
```bash
curl -X PATCH http://localhost:8000/api/graph/nodes/1/ \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'
```

---

### Delete a Node

**Endpoint:** `DELETE /api/graph/nodes/{id}/`

**Note:** Cannot delete a node that has connected edges. Delete edges first.

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/api/graph/nodes/1/
```

**Error Response (if node has edges):**
```json
{
  "error": "Cannot delete node Node_A. It is connected to 4 edge(s). Delete the edges first."
}
```

---

### Bulk Create Nodes

**Endpoint:** `POST /api/graph/nodes/bulk_create/`

**Request Body:**
```json
{
  "nodes": [
    {
      "node_id": "Node_Y",
      "map_id": "default_map",
      "x": 25.0,
      "y": 25.0,
      "theta": 0.0,
      "description": "Station Y"
    },
    {
      "node_id": "Node_Z",
      "map_id": "default_map",
      "x": 30.0,
      "y": 30.0,
      "theta": 0.0,
      "description": "Station Z"
    }
  ]
}
```

**Example Response:**
```json
{
  "message": "Successfully created 2 nodes",
  "nodes": [
    {
      "id": 11,
      "node_id": "Node_Y",
      "map_id": "default_map",
      "x": 25.0,
      "y": 25.0,
      "theta": 0.0,
      "description": "Station Y"
    },
    {
      "id": 12,
      "node_id": "Node_Z",
      "map_id": "default_map",
      "x": 30.0,
      "y": 30.0,
      "theta": 0.0,
      "description": "Station Z"
    }
  ]
}
```

---

### Bulk Delete Nodes

**Endpoint:** `POST /api/graph/nodes/bulk_delete/`

**Request Body:**
```json
{
  "node_ids": [11, 12]
}
```

**Example Response:**
```json
{
  "message": "Successfully deleted 2 node(s)"
}
```

---

### Get Node Statistics

**Endpoint:** `GET /api/graph/nodes/statistics/`

**Example Response:**
```json
{
  "total_nodes": 8,
  "maps": ["default_map"],
  "nodes_per_map": {
    "default_map": 8
  }
}
```

---

## Graph Edges API

### List All Edges

**Endpoint:** `GET /api/graph/edges/`

**Query Parameters:**
- `map_id` (optional): Filter edges by map ID
- `node_id` (optional): Filter edges connected to a specific node

**Example Request:**
```bash
curl http://localhost:8000/api/graph/edges/
curl http://localhost:8000/api/graph/edges/?node_id=Node_A
```

**Example Response:**
```json
[
  {
    "id": 1,
    "start_node": {
      "id": 1,
      "node_id": "Node_A",
      "map_id": "default_map",
      "x": 0.0,
      "y": 0.0,
      "theta": 0.0,
      "description": "Test node Node_A"
    },
    "end_node": {
      "id": 2,
      "node_id": "Node_B",
      "map_id": "default_map",
      "x": 10.0,
      "y": 0.0,
      "theta": 0.0,
      "description": "Test node Node_B"
    },
    "map_id": "default_map",
    "length": 10.0,
    "max_velocity": 2.0,
    "is_directed": true
  }
]
```

---

### Create an Edge

**Endpoint:** `POST /api/graph/edges/`

**Request Body:**
```json
{
  "start_node_id": "Node_A",
  "end_node_id": "Node_B",
  "map_id": "default_map",
  "length": 10.0,
  "max_velocity": 2.0,
  "is_directed": true
}
```

**Note:** 
- If `length` is not provided, it will be automatically calculated using Euclidean distance
- `start_node_id` and `end_node_id` must reference existing nodes

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/graph/edges/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_node_id": "Node_A",
    "end_node_id": "Node_B",
    "map_id": "default_map",
    "max_velocity": 2.0,
    "is_directed": false
  }'
```

---

### Update an Edge

**Endpoint:** `PUT /api/graph/edges/{id}/` (full update)  
**Endpoint:** `PATCH /api/graph/edges/{id}/` (partial update)

**Example Request:**
```bash
curl -X PATCH http://localhost:8000/api/graph/edges/1/ \
  -H "Content-Type: application/json" \
  -d '{"max_velocity": 3.0}'
```

---

### Delete an Edge

**Endpoint:** `DELETE /api/graph/edges/{id}/`

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/api/graph/edges/1/
```

---

### Bulk Create Edges

**Endpoint:** `POST /api/graph/edges/bulk_create/`

**Request Body:**
```json
{
  "edges": [
    {
      "start_node_id": "Node_A",
      "end_node_id": "Node_B",
      "map_id": "default_map",
      "length": 10.0,
      "max_velocity": 2.0,
      "is_directed": true
    },
    {
      "start_node_id": "Node_B",
      "end_node_id": "Node_C",
      "map_id": "default_map",
      "length": 10.0,
      "max_velocity": 2.0,
      "is_directed": true
    }
  ]
}
```

---

### Bulk Delete Edges

**Endpoint:** `POST /api/graph/edges/bulk_delete/`

**Request Body:**
```json
{
  "edge_ids": [1, 2, 3]
}
```

---

### Get Edge Statistics

**Endpoint:** `GET /api/graph/edges/statistics/`

**Example Response:**
```json
{
  "total_edges": 20,
  "directed_edges": 20,
  "bidirectional_edges": 0,
  "average_length": 10.0,
  "average_max_velocity": 2.0
}
```

---

## Graph Operations API

### Validate Graph

**Endpoint:** `GET /api/graph/validate/`

Validates the graph structure and returns issues/warnings.

**Example Response:**
```json
{
  "valid": true,
  "issues": [],
  "warnings": [
    "Node Node_X is isolated (no connections)"
  ],
  "total_nodes": 8,
  "total_edges": 20
}
```

---

### Export Graph

**Endpoint:** `GET /api/graph/export/`

**Query Parameters:**
- `map_id` (optional): Export only nodes/edges from a specific map

**Example Request:**
```bash
curl http://localhost:8000/api/graph/export/
curl http://localhost:8000/api/graph/export/?map_id=default_map
```

**Example Response:**
```json
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

---

### Import Graph

**Endpoint:** `POST /api/graph/import/`

Import a complete graph structure (bulk create nodes and edges).

**Request Body:**
```json
{
  "clear_existing": false,
  "nodes": [
    {
      "node_id": "Node_A",
      "map_id": "warehouse_1",
      "x": 0.0,
      "y": 0.0,
      "theta": 0.0,
      "description": "Start point"
    }
  ],
  "edges": [
    {
      "start_node_id": "Node_A",
      "end_node_id": "Node_B",
      "map_id": "warehouse_1",
      "length": 10.0,
      "max_velocity": 2.0,
      "is_directed": true
    }
  ]
}
```

**Parameters:**
- `clear_existing` (optional, default: false): If true, deletes all existing nodes and edges before importing

**Example Response:**
```json
{
  "message": "Import completed: 8 nodes, 20 edges",
  "created_nodes": 8,
  "created_edges": 20,
  "errors": []
}
```

---

## Error Responses

### Validation Errors

**Status Code:** `400 Bad Request`

```json
{
  "node_id": ["Node with node_id 'Node_A' already exists."],
  "x": ["X coordinate must be between -1000 and 1000"]
}
```

### Not Found

**Status Code:** `404 Not Found`

```json
{
  "detail": "Not found."
}
```

### Constraint Violations

**Status Code:** `400 Bad Request`

```json
{
  "error": "Cannot delete node Node_A. It is connected to 4 edge(s). Delete the edges first."
}
```

---

## Integration with ReactFlow

When fetching graph data for ReactFlow visualization:

1. **Fetch nodes:** `GET /api/graph/nodes/`
2. **Fetch edges:** `GET /api/graph/edges/`
3. **Transform to ReactFlow format:**

```typescript
// Transform nodes
const reactFlowNodes = nodes.map(node => ({
  id: node.node_id,
  position: { x: node.x, y: node.y },
  data: {
    label: node.node_id,
    description: node.description,
  },
  type: 'default'
}))

// Transform edges
const reactFlowEdges = edges.map(edge => ({
  id: edge.id.toString(),
  source: edge.start_node.node_id,
  target: edge.end_node.node_id,
  label: `${edge.length}m`,
  animated: !edge.is_directed,
}))
```

---

## Testing the APIs

### Using curl

```bash
# List all nodes
curl http://localhost:8000/api/graph/nodes/

# Create a node
curl -X POST http://localhost:8000/api/graph/nodes/ \
  -H "Content-Type: application/json" \
  -d '{"node_id": "TestNode", "map_id": "test", "x": 0, "y": 0}'

# List all edges
curl http://localhost:8000/api/graph/edges/

# Validate graph
curl http://localhost:8000/api/graph/validate/

# Export graph
curl http://localhost:8000/api/graph/export/ > graph_backup.json
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Create a node
response = requests.post(
    f"{BASE_URL}/graph/nodes/",
    json={
        "node_id": "Node_Test",
        "map_id": "default_map",
        "x": 50.0,
        "y": 50.0,
        "theta": 0.0,
        "description": "Test node"
    }
)
print(response.json())

# Create an edge
response = requests.post(
    f"{BASE_URL}/graph/edges/",
    json={
        "start_node_id": "Node_A",
        "end_node_id": "Node_Test",
        "map_id": "default_map",
        "max_velocity": 2.5,
        "is_directed": False
    }
)
print(response.json())
```

---

## Next Steps

1. Start the Django backend: `docker-compose up -d` (from `agv-system/` directory)
2. Set up test graph: `docker-compose exec web python manage.py setup_test_graph`
3. Test the APIs using curl or Postman
4. Integrate with the React frontend (ReactFlow)

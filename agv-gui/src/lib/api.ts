import type { Agv } from "@/types/agv"

/**
 * API base URL for Django backend
 * Default: http://localhost:8000/api
 */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

/**
 * API service for AGV fleet management
 * Communicates with Django backend (vda5050/views.py - AGVViewSet)
 */

/**
 * Fetches all AGVs from the backend
 */
export async function fetchAgvs(): Promise<Agv[]> {
  const response = await fetch(`${API_BASE_URL}/agvs/`)

  if (!response.ok) {
    throw new Error(`Failed to fetch AGVs: ${response.statusText}`)
  }

  const data: Agv[] = await response.json()
  return data.sort((a, b) =>
    a.serial_number.localeCompare(b.serial_number, undefined, {
      numeric: true,
      sensitivity: "base",
    })
  )
}

/**
 * Fetches a single AGV by serial number
 */
export async function fetchAgvBySerialNumber(
  serialNumber: string
): Promise<Agv> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/`)

  if (!response.ok) {
    throw new Error(`Failed to fetch AGV: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Creates a new AGV
 * Returns the created AGV with auto-generated id
 */
export async function createAgv(agv: Omit<Agv, "id">): Promise<Agv> {
  const response = await fetch(`${API_BASE_URL}/agvs/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(agv),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to create AGV: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Updates an existing AGV by serial number
 * Uses PATCH for partial updates
 */
export async function updateAgv(
  serialNumber: string,
  agv: Partial<Agv>
): Promise<Agv> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(agv),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to update AGV: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Deletes an AGV by serial number
 */
export async function deleteAgv(serialNumber: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/`, {
    method: "DELETE",
  })

  if (!response.ok) {
    throw new Error(`Failed to delete AGV: ${response.statusText}`)
  }
}

/**
 * Deletes all AGVs by making individual DELETE requests
 * Handles duplicate serial numbers by catching errors
 */
export async function deleteAllAgvs(): Promise<void> {
  const existingAgvs = await fetchAgvs()

  // Delete by serial number, but handle duplicates gracefully
  const processedSerials = new Set<string>()

  for (const agv of existingAgvs) {
    if (!processedSerials.has(agv.serial_number)) {
      try {
        await deleteAgv(agv.serial_number)
        processedSerials.add(agv.serial_number)
      } catch (error) {
        // If delete fails, skip this one and continue
        console.warn(`Failed to delete AGV ${agv.serial_number}:`, error)
      }
    }
  }

  // Verify all AGVs are deleted by checking the count
  const remainingAgvs = await fetchAgvs()
  if (remainingAgvs.length > 0) {
    throw new Error(
      `Failed to delete all AGVs. ${remainingAgvs.length} AGVs remain.`
    )
  }
}

/**
 * Simple CSV import: Replace all AGVs with CSV data
 * 1. Delete all existing AGVs
 * 2. Create all AGVs from CSV
 */
export async function replaceAllAgvs(agvs: Omit<Agv, "id">[]): Promise<{
  success: boolean
  created: number
  error?: string
}> {
  try {
    // Step 1: Delete all existing AGVs
    await deleteAllAgvs()

    // Step 2: Create all new AGVs from CSV
    let created = 0
    for (const agv of agvs) {
      await createAgv(agv)
      created++
    }

    return { success: true, created }
  } catch (error) {
    return {
      success: false,
      created: 0,
      error: error instanceof Error ? error.message : String(error),
    }
  }
}

// ============================================
// GRAPH API
// ============================================

export interface GraphNode {
  id: number
  node_id: string
  map_id: string
  x: number
  y: number
  theta: number
  description: string
}

export interface GraphEdge {
  id: number
  start_node: GraphNode
  end_node: GraphNode
  start_node_id?: string
  end_node_id?: string
  map_id: string
  length: number
  max_velocity: number
  is_directed: boolean
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/**
 * Fetch all graph nodes
 */
export async function fetchGraphNodes(
  mapId: string = "default_map"
): Promise<GraphNode[]> {
  const response = await fetch(`${API_BASE_URL}/graph/nodes/?map_id=${mapId}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch graph nodes: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Fetch all graph edges
 */
export async function fetchGraphEdges(
  mapId: string = "default_map"
): Promise<GraphEdge[]> {
  const response = await fetch(`${API_BASE_URL}/graph/edges/?map_id=${mapId}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch graph edges: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Fetch complete graph (nodes + edges)
 */
export async function fetchGraph(
  mapId: string = "default_map"
): Promise<GraphData> {
  const [nodes, edges] = await Promise.all([
    fetchGraphNodes(mapId),
    fetchGraphEdges(mapId),
  ])

  return { nodes, edges }
}

/**
 * Create a new graph node
 */
export async function createGraphNode(
  node: Omit<GraphNode, "id">
): Promise<GraphNode> {
  const response = await fetch(`${API_BASE_URL}/graph/nodes/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(node),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to create node: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Update an existing graph node
 */
export async function updateGraphNode(
  id: number,
  node: Partial<GraphNode>
): Promise<GraphNode> {
  const response = await fetch(`${API_BASE_URL}/graph/nodes/${id}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(node),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to update node: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Delete a graph node
 */
export async function deleteGraphNode(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/graph/nodes/${id}/`, {
    method: "DELETE",
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to delete node: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }
}

/**
 * Create a new graph edge
 */
export async function createGraphEdge(edge: {
  start_node_id: string
  end_node_id: string
  map_id: string
  max_velocity?: number
  is_directed?: boolean
}): Promise<GraphEdge> {
  const response = await fetch(`${API_BASE_URL}/graph/edges/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(edge),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to create edge: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Update an existing graph edge
 */
export async function updateGraphEdge(
  id: number,
  edge: Partial<{
    start_node_id: string
    end_node_id: string
    max_velocity: number
    is_directed: boolean
  }>
): Promise<GraphEdge> {
  const response = await fetch(`${API_BASE_URL}/graph/edges/${id}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(edge),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to update edge: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Delete a graph edge
 */
export async function deleteGraphEdge(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/graph/edges/${id}/`, {
    method: "DELETE",
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Failed to delete edge: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }
}

// ============================================
// TASK & ORDER API (VDA5050 Transport Orders)
// ============================================

/**
 * VDA5050 Node structure
 * Represents a waypoint in the AGV's path
 */
export interface VDA5050Node {
  nodeId: string
  sequenceId: number
  released: boolean
  actions: unknown[]
  nodePosition: {
    x: number
    y: number
    mapId: string
  }
}

/**
 * VDA5050 Edge structure
 * Represents a path segment between two nodes
 */
export interface VDA5050Edge {
  edgeId: string
  sequenceId: number
  startNodeId: string
  endNodeId: string
  released: boolean
  maxSpeed: number
}

/**
 * Order status lifecycle
 * Follows VDA5050 standard + backend extensions
 */
export type OrderStatus =
  | "CREATED" // Just created, will be sent to AGV
  | "SENT" // Sent via MQTT to AGV
  | "ACTIVE" // AGV is executing the order
  | "QUEUED" // Waiting for previous order to complete
  | "COMPLETED" // Successfully finished
  | "REJECTED" // AGV rejected the order
  | "CANCELLED" // Manually cancelled
  | "FAILED" // Execution failed

/**
 * Transport Order
 * Matches Django Order model (vda5050/models.py)
 */
export interface Order {
  id: number
  agv: number // AGV ID reference
  header_id: number
  timestamp: string // ISO format
  order_id: string // Unique order ID (e.g., "ORD_A3F2B8C1")
  order_update_id: number
  zone_set_id: string
  status: OrderStatus
  nodes: VDA5050Node[]
  edges: VDA5050Edge[]
  rejection_reason?: string
  created_at: string // ISO format
  updated_at: string // ISO format
}

/**
 * Task creation request
 * Sent to /api/tasks/ to trigger auction
 */
export interface TaskRequest {
  pickup_node_id: string
  delivery_node_id: string
}

/**
 * Task creation response
 * Contains auction results and created order info
 */
export interface TaskResponse {
  success: boolean
  order_id: string
  winner_agv: string
  status: OrderStatus
  message: string
  pickup_node: string
  delivery_node: string
  path: string[] // Array of node IDs in execution order
  error?: string
}

/**
 * AGV State (Telemetry)
 * Matches Django AGVState model (vda5050/models.py)
 */
export interface AGVState {
  id: number
  header_id: number
  timestamp: string // ISO format (from AGV)
  received_at: string // ISO format (server time)
  order_id: string
  last_node_id: string
  last_node_sequence_id: number
  driving: boolean
  paused: boolean
  operating_mode: string
  battery_state: {
    batteryCharge: number // Percentage (0-100)
    batteryVoltage: number // Volts
    batteryHealth: number // Percentage (0-100)
  }
  agv_position: {
    x: number
    y: number
    theta: number // Radians
    mapId: string
    positionInitialized: boolean
  }
  velocity: {
    vx: number // m/s
    vy: number // m/s
    omega: number // rad/s
  }
  safety_state: {
    eStop: string // "NONE", "AUTOACK", "MANUAL"
    fieldViolation: boolean
  }
  errors: unknown[]
  loads: unknown[]
}

/**
 * Creates a transport task (pickup → delivery)
 * Triggers the auction-based bidding system
 * Returns the winning AGV and created order
 *
 * @param task - Pickup and delivery node IDs
 * @returns Auction results with winner AGV and order details
 * @throws Error if no AGVs available or no path exists
 */
export async function createTask(task: TaskRequest): Promise<TaskResponse> {
  const response = await fetch(`${API_BASE_URL}/tasks/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(task),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      `Task creation failed: ${response.statusText} - ${JSON.stringify(errorData)}`
    )
  }

  return response.json()
}

/**
 * Fetches all orders from the backend
 * Orders are returned newest first
 *
 * @returns Array of all orders
 */
export async function fetchOrders(): Promise<Order[]> {
  const response = await fetch(`${API_BASE_URL}/orders/`)

  if (!response.ok) {
    throw new Error(`Failed to fetch orders: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Fetches a single order by ID
 *
 * @param orderId - Database ID of the order
 * @returns Order details
 */
export async function fetchOrder(orderId: number): Promise<Order> {
  const response = await fetch(`${API_BASE_URL}/orders/${orderId}/`)

  if (!response.ok) {
    throw new Error(`Failed to fetch order: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Fetches AGV state history (latest 100 states)
 * States are returned newest first
 *
 * @param serialNumber - AGV serial number
 * @returns Array of state snapshots
 */
export async function fetchAgvStates(
  serialNumber: string
): Promise<AGVState[]> {
  const response = await fetch(`${API_BASE_URL}/agvs/${serialNumber}/states/`)

  if (!response.ok) {
    throw new Error(`Failed to fetch AGV states: ${response.statusText}`)
  }

  return response.json()
}

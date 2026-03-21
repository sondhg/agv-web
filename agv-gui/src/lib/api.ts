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

  return response.json()
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
  mapId: string = "map_1"
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
  mapId: string = "map_1"
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
export async function fetchGraph(mapId: string = "map_1"): Promise<GraphData> {
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

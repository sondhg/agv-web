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
    throw new Error(`Failed to delete all AGVs. ${remainingAgvs.length} AGVs remain.`)
  }
}

/**
 * Simple CSV import: Replace all AGVs with CSV data
 * 1. Delete all existing AGVs
 * 2. Create all AGVs from CSV
 */
export async function replaceAllAgvs(
  agvs: Omit<Agv, "id">[]
): Promise<{
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

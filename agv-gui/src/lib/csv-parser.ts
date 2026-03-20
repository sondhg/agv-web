import type { Agv } from "@/types/agv"

/**
 * Parses CSV file containing AGV registration data
 * Matches Django backend AGV model (vda5050/models.py)
 *
 * Required fields: manufacturer, serial_number
 * Optional fields: description, protocol_version, current_map_id
 */
export function parseCSV(csvText: string): Agv[] {
  const lines = csvText.trim().split("\n")
  if (lines.length < 2) {
    throw new Error("CSV file must have at least a header row and one data row")
  }

  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase())

  const requiredHeaders = ["manufacturer", "serial_number"]
  const missingHeaders = requiredHeaders.filter((h) => !headers.includes(h))
  if (missingHeaders.length > 0) {
    throw new Error(
      `Missing required headers: ${missingHeaders.join(", ")}. Required headers are: ${requiredHeaders.join(", ")}`
    )
  }

  const agvs: Agv[] = []
  const seenPairs = new Map<string, number>() // Track manufacturer+serial_number -> row number

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue

    const values = line.split(",").map((v) => v.trim())
    const agv: Partial<Agv> = {}

    headers.forEach((header, index) => {
      const value = values[index]
      if (!value) return // Skip empty values

      switch (header) {
        case "manufacturer":
          agv.manufacturer = value
          break
        case "serial_number":
          agv.serial_number = value
          break
        case "description":
          agv.description = value
          break
        case "protocol_version":
          agv.protocol_version = value
          break
        case "current_map_id":
          agv.current_map_id = value
          break
      }
    })

    // Validate required fields
    if (agv.manufacturer && agv.serial_number) {
      // Check for duplicates in CSV
      const key = `${agv.manufacturer}|${agv.serial_number}`
      if (seenPairs.has(key)) {
        const firstRow = seenPairs.get(key)!
        throw new Error(
          `Duplicate AGV found in CSV:\n` +
            `Manufacturer: "${agv.manufacturer}", Serial Number: "${agv.serial_number}"\n` +
            `First occurrence: row ${firstRow + 1}\n` +
            `Duplicate found: row ${i + 1}\n\n` +
            `Each AGV must have a unique combination of manufacturer and serial_number.`
        )
      }
      seenPairs.set(key, i)
      agvs.push(agv as Agv)
    } else {
      console.warn(`Skipping row ${i + 1}: Missing required fields`)
    }
  }

  return agvs
}

/**
 * Exports AGV data to CSV format
 */
export function exportToCSV(agvs: Agv[]): string {
  if (agvs.length === 0) return ""

  const headers = [
    "manufacturer",
    "serial_number",
    "description",
    "protocol_version",
    "current_map_id",
  ]

  const rows = agvs.map((agv) =>
    [
      agv.manufacturer,
      agv.serial_number,
      agv.description ?? "",
      agv.protocol_version ?? "",
      agv.current_map_id ?? "",
    ].join(",")
  )

  return [headers.join(","), ...rows].join("\n")
}

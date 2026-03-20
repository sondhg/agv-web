"use client"

import type { ColumnDef } from "@tanstack/react-table"

import type { Agv } from "@/types/agv"

/**
 * Table columns for AGV fleet registration
 * Displays AGV data matching Django backend model
 */
export const columns: ColumnDef<Agv>[] = [
  {
    accessorKey: "manufacturer",
    header: "Manufacturer",
    cell: ({ row }) => {
      const manufacturer = row.getValue("manufacturer") as string
      return <span className="font-medium">{manufacturer}</span>
    },
  },
  {
    accessorKey: "serial_number",
    header: "Serial Number",
    cell: ({ row }) => {
      const serialNumber = row.getValue("serial_number") as string
      return (
        <span className="font-mono text-sm text-muted-foreground">
          {serialNumber}
        </span>
      )
    },
  },
  {
    accessorKey: "protocol_version",
    header: "Protocol Version",
    cell: ({ row }) => {
      const version = row.getValue("protocol_version") as string | undefined
      return version ? (
        <span className="text-sm">{version}</span>
      ) : (
        <span className="text-sm text-muted-foreground">N/A</span>
      )
    },
  },
  {
    accessorKey: "current_map_id",
    header: "Current Map",
    cell: ({ row }) => {
      const mapId = row.getValue("current_map_id") as string | undefined
      return mapId ? (
        <span className="text-sm">{mapId}</span>
      ) : (
        <span className="text-sm text-muted-foreground">N/A</span>
      )
    },
  },
  {
    accessorKey: "is_online",
    header: "Status",
    cell: ({ row }) => {
      const isOnline = row.getValue("is_online") as boolean | undefined
      return (
        <span
          className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
            isOnline
              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
              : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
          }`}
        >
          {isOnline === undefined ? "Unknown" : isOnline ? "Online" : "Offline"}
        </span>
      )
    },
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => {
      const description = row.getValue("description") as string | undefined
      return description ? (
        <span className="text-sm">{description}</span>
      ) : (
        <span className="text-sm text-muted-foreground">—</span>
      )
    },
  },
]

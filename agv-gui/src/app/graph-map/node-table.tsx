"use client"

import type { ColumnDef } from "@tanstack/react-table"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import type { Node } from "@xyflow/react"
import { getNodeColor } from "./utils"

interface NodeTableProps {
  nodes: Node[]
  updateNodeType: (
    nodeId: string,
    nodeType: "DEFAULT" | "PICKUP" | "DELIVERY" | "CHARGING"
  ) => void
}

export function NodeTable({ nodes, updateNodeType }: NodeTableProps) {
  const columns: ColumnDef<Node>[] = [
    {
      accessorKey: "id",
      header: "Node ID",
      cell: ({ row }) => <div className="font-semibold">{row.original.id}</div>,
    },
    {
      accessorKey: "data.node_type",
      header: "Node Type",
      cell: ({ row }) => {
        const nodeType = (row.original.data?.node_type as string) || "DEFAULT"
        return (
          <div className="flex items-center gap-3">
            <div
              className="h-4 w-4 rounded-full shadow-sm"
              style={{ backgroundColor: getNodeColor(nodeType) }}
            />
            <Select
              value={nodeType}
              onValueChange={(
                val: "DEFAULT" | "PICKUP" | "DELIVERY" | "CHARGING"
              ) => updateNodeType(row.original.id, val)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem
                  value="DEFAULT"
                  style={{ color: getNodeColor("DEFAULT") }}
                >
                  Default / Transit
                </SelectItem>
                <SelectItem
                  value="PICKUP"
                  style={{ color: getNodeColor("PICKUP") }}
                >
                  Pickup Station
                </SelectItem>
                <SelectItem
                  value="DELIVERY"
                  style={{ color: getNodeColor("DELIVERY") }}
                >
                  Delivery Station
                </SelectItem>
                <SelectItem
                  value="CHARGING"
                  style={{ color: getNodeColor("CHARGING") }}
                >
                  Charging Station
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        )
      },
    },
    {
      accessorKey: "data.dbId",
      header: "DB ID",
      cell: ({ row }) => row.original.data?.dbId ?? "New Node",
    },
    {
      accessorKey: "position.x",
      header: "X Position",
      cell: ({ row }) => row.original.position.x.toFixed(2),
    },
    {
      accessorKey: "position.y",
      header: "Y Position",
      cell: ({ row }) => row.original.position.y.toFixed(2),
    },
  ]

  const table = useReactTable({
    data: nodes,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="rounded-md border shadow">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                return (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && "selected"}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                No nodes found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}

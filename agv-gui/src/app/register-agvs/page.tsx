"use client"

import { Upload, Loader2 } from "lucide-react"
import * as React from "react"

import { Button } from "@/components/ui/button"
import { replaceAllAgvs, fetchAgvs } from "@/lib/api"
import { parseCSV } from "@/lib/csv-parser"
import type { Agv } from "@/types/agv"

import { columns } from "./columns"
import { DataTable } from "./data-table"

export default function RegisterAgvPage() {
  const [agvs, setAgvs] = React.useState<Agv[]>([])
  const [error, setError] = React.useState<string | null>(null)
  const [success, setSuccess] = React.useState<string | null>(null)
  const [isLoading, setIsLoading] = React.useState(false)
  const [isUploading, setIsUploading] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  // Fetch AGVs on mount
  React.useEffect(() => {
    loadAgvs()
  }, [])

  const loadAgvs = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchAgvs()
      setAgvs(data)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load AGV fleet data"
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith(".csv")) {
      setError("Please upload a CSV file")
      return
    }

    const reader = new FileReader()

    reader.onload = async (e) => {
      setIsUploading(true)
      setError(null)
      setSuccess(null)

      try {
        const text = e.target?.result as string
        const parsedAgvs = parseCSV(text)

        // Replace all AGVs with CSV data
        const result = await replaceAllAgvs(parsedAgvs)

        if (result.success) {
          setSuccess(`Successfully imported ${result.created} AGV(s)`)
          await loadAgvs()
        } else {
          setError(result.error || "Failed to import CSV")
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to process CSV file"
        )
      } finally {
        setIsUploading(false)
      }
    }

    reader.onerror = () => {
      setError("Failed to read file")
      setIsUploading(false)
    }

    reader.readAsText(file)

    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleButtonClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="container mx-auto space-y-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            AGV Fleet Registration
          </h1>
          <p className="text-muted-foreground">
            Register and manage physical AGVs in your fleet
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            className="hidden"
            aria-label="Upload CSV file"
          />
          <Button
            onClick={handleButtonClick}
            className="cursor-pointer gap-2"
            disabled={isUploading}
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {isUploading ? "Uploading..." : "Import CSV"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive dark:border-destructive/50 dark:bg-destructive/20">
          <strong>Error:</strong>{" "}
          <span className="whitespace-pre-wrap">{error}</span>
        </div>
      )}

      {success && (
        <div className="rounded-lg border border-green-500 bg-green-50 p-4 text-sm text-green-800 dark:border-green-500/50 dark:bg-green-900/20 dark:text-green-100">
          <strong>Success:</strong> {success}
        </div>
      )}

      <div className="rounded-lg border bg-card p-6">
        <div className="mb-4 space-y-1">
          <h2 className="text-xl font-semibold">Registered AGVs</h2>
          <p className="text-sm text-muted-foreground">
            List of all physical AGVs registered in the fleet. Upload a CSV file
            to sync the fleet (will overwrite existing data).
          </p>
        </div>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <DataTable columns={columns} data={agvs} />
        )}
      </div>

      <div className="rounded-lg border bg-muted/50 p-4 text-sm dark:bg-muted/20">
        <h3 className="mb-2 font-semibold">CSV Format</h3>
        <p className="mb-2 text-muted-foreground">
          Your CSV file should have the following headers (required fields are
          marked with *):
        </p>
        <code className="block rounded bg-muted px-2 py-1 font-mono text-xs dark:bg-muted/50">
          manufacturer*,serial_number*,description,protocol_version,current_map_id
        </code>
        <div className="mt-3 space-y-1 text-muted-foreground">
          <p>
            <strong>manufacturer*:</strong> AGV manufacturer name (e.g., "KUKA",
            "ABB")
          </p>
          <p>
            <strong>serial_number*:</strong> Unique serial number for the AGV
          </p>
          <p>
            <strong>description:</strong> Optional description of the AGV
          </p>
          <p>
            <strong>protocol_version:</strong> VDA5050 protocol version (e.g.,
            "2.1.0")
          </p>
          <p>
            <strong>current_map_id:</strong> Current map identifier
          </p>
        </div>
        <div className="mt-3 rounded border border-yellow-500 bg-yellow-50 p-2 text-xs dark:border-yellow-500/50 dark:bg-yellow-900/20">
          <p className="font-semibold text-yellow-800 dark:text-yellow-100">
            ⚠️ Important: CSV Import Behavior
          </p>
          <p className="mt-1 text-yellow-700 dark:text-yellow-200">
            Importing a CSV will <strong>completely overwrite</strong> your
            fleet data. AGVs not listed in the CSV will be deleted. The CSV file
            becomes the single source of truth for your fleet.
          </p>
        </div>
        <div className="mt-3 rounded border border-yellow-500 bg-yellow-50 p-2 text-xs dark:border-yellow-500/50 dark:bg-yellow-900/20">
          <p className="mt-1 text-yellow-700 dark:text-yellow-200">
            Note: serial_number must be unique.
          </p>
        </div>
      </div>
    </div>
  )
}

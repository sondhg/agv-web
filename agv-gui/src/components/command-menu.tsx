import { useState, useEffect } from "react"

import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"

interface CommandMenuProps {
  onNavigate: (path: string) => void
}

export function CommandMenu({ onNavigate }: CommandMenuProps) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const runCommand = (path: string) => {
    setOpen(false)
    onNavigate(path)
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <Command>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Navigation">
            <CommandItem onSelect={() => runCommand("/dashboard")}>
              Dashboard
            </CommandItem>
            <CommandItem onSelect={() => runCommand("/fleet")}>
              Fleet Dashboard
            </CommandItem>
            <CommandItem onSelect={() => runCommand("/orders")}>
              Orders
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Supervise">
            <CommandItem onSelect={() => runCommand("/supervise/task-bidding")}>
              Task Bidding
            </CommandItem>
            <CommandItem onSelect={() => runCommand("/supervise/sensor-data")}>
              Sensor Data
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Simulate & Tasks">
            <CommandItem onSelect={() => runCommand("/simulate/routing")}>
              Routing
            </CommandItem>
            <CommandItem onSelect={() => runCommand("/tasks/create")}>
              Create Task
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="User Inputs">
            <CommandItem onSelect={() => runCommand("/user-inputs/graph-map")}>
              Graph Map
            </CommandItem>
            <CommandItem onSelect={() => runCommand("/user-inputs/register-agvs")}>
              Register AGVs
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}

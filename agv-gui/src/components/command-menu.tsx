import { useState, useEffect } from "react"
import { ROUTES, type RoutePath } from "@/config/routes"

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
  onNavigate: (path: RoutePath) => void
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

  const runCommand = (path: RoutePath) => {
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
            <CommandItem onSelect={() => runCommand(ROUTES.DASHBOARD)}>
              Analytics Dashboard
            </CommandItem>
            <CommandItem onSelect={() => runCommand(ROUTES.FLEET)}>
              Fleet Dashboard
            </CommandItem>
            <CommandItem onSelect={() => runCommand(ROUTES.ORDERS)}>
              Orders
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Supervise">
            <CommandItem
              onSelect={() => runCommand(ROUTES.SUPERVISE_TASK_BIDDING)}
            >
              Task Bidding
            </CommandItem>
            <CommandItem
              onSelect={() => runCommand(ROUTES.SUPERVISE_SENSOR_DATA)}
            >
              Sensor Data
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Simulate & Tasks">
            <CommandItem onSelect={() => runCommand(ROUTES.SIMULATE_ROUTING)}>
              Routing
            </CommandItem>
            <CommandItem onSelect={() => runCommand(ROUTES.TASKS_CREATE)}>
              Create Task
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="User Inputs">
            <CommandItem
              onSelect={() => runCommand(ROUTES.USER_INPUTS_GRAPH_MAP)}
            >
              Graph Map
            </CommandItem>
            <CommandItem
              onSelect={() => runCommand(ROUTES.USER_INPUTS_REGISTER_AGVS)}
            >
              Register AGVs
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}

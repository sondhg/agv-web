import { Outlet, useRouterState, useNavigate } from "@tanstack/react-router"

import { AppSidebar } from "@/components/app-sidebar"
import { CommandMenu } from "@/components/command-menu"
import { ROUTES, type RoutePath } from "@/config/routes"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"

const routeToBreadcrumb: Record<string, string> = {
  [ROUTES.HOME]: "Dashboard",
  [ROUTES.DASHBOARD]: "Dashboard",
  [ROUTES.FLEET]: "Fleet Dashboard",
  [ROUTES.ORDERS]: "Orders",
  [ROUTES.TASKS_CREATE]: "Create Task",
  "/user-inputs": "User Inputs", // Parent route grouping
  [ROUTES.USER_INPUTS_REGISTER_AGVS]: "Register AGVs",
  [ROUTES.USER_INPUTS_GRAPH_MAP]: "Graph Map",
  [ROUTES.SUPERVISE_TASK_BIDDING]: "Task Bidding",
  [ROUTES.SUPERVISE_SENSOR_DATA]: "Sensor Data",
  [ROUTES.SIMULATE_ROUTING]: "Routing",
}

export default function Layout() {
  const routerState = useRouterState()
  const navigate = useNavigate()
  const currentPath = routerState.location.pathname
  const breadcrumbTitle = routeToBreadcrumb[currentPath] || "Dashboard"

  const handleNavigate = (path: RoutePath) => {
    navigate({ to: path })
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator
            orientation="vertical"
            className="mr-2 data-[orientation=vertical]:h-4"
          />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem className="hidden md:block">
                <BreadcrumbLink href="/">AGV Web App</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>{breadcrumbTitle}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="ml-auto font-mono text-xs text-muted-foreground">
            (Press <kbd>d</kbd> to toggle dark mode, <kbd>Ctrl+B</kbd> to toggle
            sidebar, <kbd>Ctrl+K</kbd> to search)
          </div>
        </header>
        <main className="px-4">
          <Outlet />
        </main>
      </SidebarInset>
      <CommandMenu onNavigate={handleNavigate} />
    </SidebarProvider>
  )
}

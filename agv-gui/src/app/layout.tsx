import { Outlet, useRouterState } from "@tanstack/react-router"

import { AppSidebar } from "@/components/app-sidebar"
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
  "/": "Dashboard",
  "/dashboard": "Dashboard",
  "/user-inputs": "User Inputs",
  "/supervise/task-bidding": "Task Bidding",
  "/supervise/sensor-data": "Sensor Data",
  "/simulate/routing": "Routing",
}

export default function Layout() {
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname
  const breadcrumbTitle = routeToBreadcrumb[currentPath] || "Dashboard"

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
            sidebar)
          </div>
        </header>
        <main className="px-4">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

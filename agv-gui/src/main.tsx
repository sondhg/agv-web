import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { MqttProvider } from "@/contexts/MqttContext"
import { Toaster } from "@/components/ui/sonner"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <MqttProvider>
        <App />
        <Toaster />
      </MqttProvider>
    </ThemeProvider>
  </StrictMode>
)

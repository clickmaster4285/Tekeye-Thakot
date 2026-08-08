import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { registerSW } from "virtual:pwa-register"
import { router } from "./routes"
import "./index.css"

registerSW({
  immediate: true,
  onRegisteredSW(_swUrl, registration) {
    if (!registration) return
    const check = () => {
      void registration.update()
    }
    // Pick up new deployments after you publish a build (browser still checks SW on navigation too).
    window.setInterval(check, 30 * 60 * 1000)
    window.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") check()
    })
  },
})

const queryClient = new QueryClient()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
)

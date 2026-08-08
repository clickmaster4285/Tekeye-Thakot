import { useEffect, useRef } from "react"
import { useLocation } from "react-router-dom"
import { reportActivityLog } from "@/lib/logs-api"
import { ROUTES } from "@/routes/config"

/**
 * Reports the current route as an activity for full-app logs. Renders nothing.
 * Only runs when user is authenticated (DashboardLayout is only shown when logged in).
 */
export function ActivityLogger() {
  const location = useLocation()
  const prevPathRef = useRef<string | null>(null)

  useEffect(() => {
    const pathname = location.pathname || "/"
    if (pathname === ROUTES.LOGIN) return
    if (prevPathRef.current === pathname) return
    prevPathRef.current = pathname
    const action = pathname === "/" || pathname === "" ? "Viewed / (Dashboard)" : `Viewed ${pathname}`
    // Fire-and-forget: the logger must never crash the app if backend is unavailable.
    void reportActivityLog(action)
  }, [location.pathname])

  return null
}

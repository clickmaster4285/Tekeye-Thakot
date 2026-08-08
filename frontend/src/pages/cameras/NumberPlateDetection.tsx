import { useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Car,
  ChevronLeft,
  ChevronRight,
  Filter,
  Flame,
  RefreshCw,
  Search,
  Truck,
  X,
} from "lucide-react"
import { ModulePageLayout } from "@/components/dashboard/module-page-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DetectionSnapshotThumb } from "@/components/cameras/detection-snapshot-thumb"
import {
  fetchDetectionEventsPage,
  fetchCameras,
  fetchSites,
  type DetectionEventsQuery,
  type SiteRecord,
} from "@/lib/cameras-api"

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const
const DEFAULT_PAGE_SIZE = 25

/** This deployment is Thakot-only — never query other sites. */
const SITE_CODE = "THAKOT"

/** Allowed vehicle classes for this panel (must match backend vehicle_only). */
const VEHICLE_CLASSES = new Set([
  "car",
  "truck",
  "bus",
  "motorcycle",
  "bicycle",
  "vehicle",
  "van",
])

type AppliedFilters = {
  q: string
  camera: string
  date_from: string
  date_to: string
  class_name: string
}

const emptyFilters: AppliedFilters = {
  q: "",
  camera: "all",
  date_from: "",
  date_to: "",
  class_name: "all",
}

function resolveThakotSiteCode(sites: SiteRecord[]): string {
  const match = sites.find(
    (s) =>
      s.code?.toUpperCase() === SITE_CODE ||
      s.name?.toLowerCase().includes("thakot") ||
      s.code?.toLowerCase().includes("thakot")
  )
  return match?.code || SITE_CODE
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  } catch {
    return iso
  }
}

function confidenceTone(confidence: number): string {
  if (confidence >= 0.85) return "bg-emerald-500"
  if (confidence >= 0.6) return "bg-amber-500"
  return "bg-orange-500"
}

function buildQuery(
  page: number,
  pageSize: number,
  filters: AppliedFilters,
  siteCode: string
): DetectionEventsQuery {
  const query: DetectionEventsQuery = {
    page,
    page_size: pageSize,
    vehicle_only: true,
    site: siteCode,
  }
  if (filters.q.trim()) query.q = filters.q.trim()
  if (filters.camera !== "all") query.camera = Number(filters.camera)
  if (filters.date_from) query.date_from = filters.date_from
  if (filters.date_to) query.date_to = filters.date_to
  if (filters.class_name !== "all") query.class_name = filters.class_name
  return query
}

export default function NumberPlateDetectionPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE)
  const [pageInput, setPageInput] = useState("1")
  const [draft, setDraft] = useState<AppliedFilters>(emptyFilters)
  const [applied, setApplied] = useState<AppliedFilters>(emptyFilters)

  const { data: sites = [] } = useQuery({
    queryKey: ["sites"],
    queryFn: fetchSites,
  })

  const thakotSiteCode = useMemo(() => resolveThakotSiteCode(sites), [sites])

  const { data: cameras = [] } = useQuery({
    queryKey: ["cameras", thakotSiteCode],
    queryFn: () => fetchCameras(),
  })

  const queryParams = useMemo(
    () => buildQuery(page, pageSize, applied, thakotSiteCode),
    [page, pageSize, applied, thakotSiteCode]
  )

  const {
    data: eventsPage,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ["vehicle-detection-events", queryParams],
    queryFn: () => fetchDetectionEventsPage(queryParams),
    placeholderData: (prev) => prev,
    refetchInterval: 12_000,
    refetchOnWindowFocus: false,
  })

  const events = useMemo(
    () =>
      (eventsPage?.results ?? []).filter((row) =>
        VEHICLE_CLASSES.has(String(row.class_name || "").trim().toLowerCase())
      ),
    [eventsPage?.results]
  )
  const totalCount = eventsPage?.count ?? 0
  const totalPages = eventsPage?.total_pages ?? 0

  const siteCameras = useMemo(() => {
    const code = thakotSiteCode.toLowerCase()
    return cameras.filter(
      (c) =>
        c.site_code?.toLowerCase() === code ||
        c.location?.toLowerCase() === code ||
        c.site_code?.toLowerCase().includes("thakot") ||
        c.location?.toLowerCase().includes("thakot")
    )
  }, [cameras, thakotSiteCode])

  const hasActiveFilters = useMemo(
    () =>
      applied.q.trim() !== "" ||
      applied.camera !== "all" ||
      applied.date_from !== "" ||
      applied.date_to !== "" ||
      applied.class_name !== "all",
    [applied]
  )

  const applyFilters = () => {
    setApplied(draft)
    setPage(1)
  }

  const clearFilters = () => {
    setDraft(emptyFilters)
    setApplied(emptyFilters)
    setPage(1)
  }

  useEffect(() => {
    if (totalPages > 0 && page > totalPages) {
      setPage(totalPages)
    }
  }, [page, totalPages])

  useEffect(() => {
    setPageInput(String(page))
  }, [page])

  const goToPage = () => {
    const parsed = Number.parseInt(pageInput.trim(), 10)
    if (Number.isNaN(parsed)) {
      setPageInput(String(page))
      return
    }
    const target = Math.min(Math.max(1, parsed), Math.max(1, totalPages))
    setPage(target)
    setPageInput(String(target))
  }

  const rangeStart = totalCount === 0 ? 0 : (page - 1) * pageSize + 1
  const rangeEnd = Math.min(page * pageSize, totalCount)

  return (
    <ModulePageLayout
      title="Vehicle Detection"
      description="Thakot site — vehicle detections only (car, truck, bus, motorcycle, van, bicycle)."
      breadcrumbs={[{ label: "AI Computer Vision" }, { label: "Vehicle Detection" }]}
    >
      <div className="grid gap-6">
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="border-l-4 border-l-primary shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Vehicles listed</CardTitle>
              <Truck className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">
                {totalCount.toLocaleString()}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Matching current filters
              </p>
            </CardContent>
          </Card>
          <Card className="border-l-4 border-l-sky-500 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">On this page</CardTitle>
              <Car className="h-4 w-4 text-sky-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">{events.length}</div>
              <p className="mt-1 text-xs text-muted-foreground">
                {totalCount > 0
                  ? `Showing ${rangeStart}–${rangeEnd}`
                  : "No vehicles yet"}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-sm">
          <CardHeader className="pb-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Filter className="h-5 w-5 text-muted-foreground" />
                  Filters
                </CardTitle>
                <CardDescription>
                  Thakot only — filter by date/time, camera, and vehicle class.
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
                  <RefreshCw className={`h-4 w-4 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={clearFilters}>
                    <X className="h-4 w-4 mr-1.5" />
                    Clear filters
                  </Button>
                )}
                <Button size="sm" onClick={applyFilters}>
                  Apply filters
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <div className="min-w-0 space-y-2">
              <Label htmlFor="veh-search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="veh-search"
                  className="h-10 w-full pl-9"
                  placeholder="e.g. truck, camera code…"
                  value={draft.q}
                  onChange={(e) => setDraft((f) => ({ ...f, q: e.target.value }))}
                  onKeyDown={(e) => e.key === "Enter" && applyFilters()}
                />
              </div>
            </div>
            <div className="min-w-0 space-y-2">
              <Label>Camera</Label>
              <Select
                value={draft.camera}
                onValueChange={(v) => setDraft((f) => ({ ...f, camera: v }))}
              >
                <SelectTrigger className="h-10 w-full">
                  <SelectValue placeholder="All cameras" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Thakot cameras</SelectItem>
                  {siteCameras.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.code} · {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-0 space-y-2">
              <Label>Vehicle class</Label>
              <Select
                value={draft.class_name}
                onValueChange={(v) => setDraft((f) => ({ ...f, class_name: v }))}
              >
                <SelectTrigger className="h-10 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All vehicles</SelectItem>
                  <SelectItem value="car">Car</SelectItem>
                  <SelectItem value="truck">Truck</SelectItem>
                  <SelectItem value="bus">Bus</SelectItem>
                  <SelectItem value="motorcycle">Motorcycle</SelectItem>
                  <SelectItem value="bicycle">Bicycle</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="veh-from">Date & time from</Label>
              <Input
                id="veh-from"
                type="datetime-local"
                className="h-10 w-full"
                value={draft.date_from}
                onChange={(e) => setDraft((f) => ({ ...f, date_from: e.target.value }))}
              />
            </div>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="veh-to">Date & time to</Label>
              <Input
                id="veh-to"
                type="datetime-local"
                className="h-10 w-full"
                value={draft.date_to}
                onChange={(e) => setDraft((f) => ({ ...f, date_to: e.target.value }))}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="w-full min-w-0 shadow-sm">
          <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Detected vehicles</CardTitle>
              <CardDescription>
                {totalCount > 0
                  ? `Showing ${rangeStart}–${rangeEnd} of ${totalCount.toLocaleString()} vehicles`
                  : hasActiveFilters
                    ? "No vehicles match your filters"
                    : "No vehicle detections recorded yet"}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="veh-page-size" className="text-sm text-muted-foreground whitespace-nowrap">
                Per page
              </Label>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setPageSize(Number(v))
                  setPage(1)
                }}
              >
                <SelectTrigger id="veh-page-size" className="w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent className="w-full min-w-0 space-y-4">
            {error && (
              <div className="rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {error instanceof Error ? error.message : "Failed to load vehicle detections"}
              </div>
            )}

            <div className="w-full overflow-x-auto rounded-lg border">
              <Table className="min-w-[1000px]">
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40">
                    <TableHead className="w-[170px]">Date & time</TableHead>
                    <TableHead>Camera</TableHead>
                    <TableHead>Class</TableHead>
                    <TableHead>Label</TableHead>
                    <TableHead className="w-[140px]">Confidence</TableHead>
                    <TableHead>Alert</TableHead>
                    <TableHead className="w-[140px]">Snapshot</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                        Loading vehicle detections…
                      </TableCell>
                    </TableRow>
                  ) : events.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                        <Car className="h-8 w-8 mx-auto mb-2 opacity-40" />
                        {hasActiveFilters
                          ? "No vehicles match your filters. Try a wider date range or clear filters."
                          : "No Thakot vehicles detected yet. Enable AI on cameras and open live feeds."}
                      </TableCell>
                    </TableRow>
                  ) : (
                    events.map((row) => (
                      <TableRow key={row.id} className={row.is_alert ? "bg-amber-50/50 dark:bg-amber-950/10" : undefined}>
                        <TableCell className="font-mono text-xs whitespace-nowrap">
                          {formatDateTime(row.created_at)}
                        </TableCell>
                        <TableCell>
                          <div className="font-medium">{row.camera_code}</div>
                          <div className="text-xs text-muted-foreground truncate max-w-[160px]">
                            {row.name ?? row.camera_name ?? row.camera_code}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="font-normal capitalize">
                            {row.class_name}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[180px] truncate" title={row.label}>
                          {row.label}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="h-2 flex-1 rounded-full bg-muted overflow-hidden min-w-[72px]">
                              <div
                                className={`h-full rounded-full ${confidenceTone(row.confidence)}`}
                                style={{ width: `${Math.round(row.confidence * 100)}%` }}
                              />
                            </div>
                            <span className="text-xs font-medium tabular-nums w-9 text-right">
                              {(row.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {row.is_alert ? (
                            <Badge variant="destructive" className="gap-1">
                              <Flame className="h-3 w-3" />
                              Alert
                            </Badge>
                          ) : (
                            <Badge variant="outline">Normal</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {row.clip_url ? (
                            <DetectionSnapshotThumb row={row} />
                          ) : row.clip_status === "pending" || row.clip_status === "recording" ? (
                            <span className="text-xs text-muted-foreground">Capturing…</span>
                          ) : row.clip_status === "failed" ? (
                            <span className="text-xs text-destructive">Capture failed</span>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {totalCount > 0 && (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {page.toLocaleString()} of {totalPages.toLocaleString()}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1 || isFetching}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Previous
                  </Button>
                  <div className="flex items-center gap-1.5">
                    <Label htmlFor="veh-page-jump" className="text-sm text-muted-foreground whitespace-nowrap">
                      Go to
                    </Label>
                    <Input
                      id="veh-page-jump"
                      type="number"
                      min={1}
                      max={Math.max(1, totalPages)}
                      value={pageInput}
                      onChange={(e) => setPageInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") goToPage()
                      }}
                      placeholder="Page"
                      className="h-8 w-20 text-center tabular-nums"
                      disabled={isFetching}
                    />
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={goToPage}
                      disabled={isFetching || totalPages <= 1}
                    >
                      Go
                    </Button>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages || isFetching}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ModulePageLayout>
  )
}

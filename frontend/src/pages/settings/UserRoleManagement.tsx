import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Users, Shield, UserPlus, Loader2, Eye, Pencil, Trash2 } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { ModulePageLayout } from "@/components/dashboard/module-page-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { getStoredToken } from "@/lib/api"
import {
  canDeleteUser,
  deleteUser,
  fetchUsers,
  ROLE_OPTIONS,
  locationLabel,
  roleLabel,
  type ApiUser,
} from "@/lib/users-api"
import { ROUTES, getUserDetailPath, getUserEditPath } from "@/routes/config"

export default function UserRoleManagementPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [deleteTarget, setDeleteTarget] = useState<ApiUser | null>(null)
  const [deleting, setDeleting] = useState(false)

  const hasAuth = Boolean(getStoredToken())

  const {
    data: users = [],
    isLoading,
    error: loadError,
  } = useQuery({
    queryKey: ["users", "list"],
    queryFn: fetchUsers,
    enabled: hasAuth,
  })

  const openAddForm = () => {
    if (!hasAuth) {
      toast({
        title: "Sign in required",
        description: "Log in as Admin or HR to create users in the database.",
        variant: "destructive",
      })
      return
    }
    navigate(ROUTES.ADD_USER)
  }

  const openEditForm = (user: ApiUser) => {
    if (!hasAuth) {
      toast({
        title: "Sign in required",
        description: "Log in as Admin or HR to edit users.",
        variant: "destructive",
      })
      return
    }
    navigate(getUserEditPath(user.id))
  }

  const openView = (user: ApiUser) => {
    if (!hasAuth) return
    navigate(getUserDetailPath(user.id))
  }

  const confirmDelete = async () => {
    if (!deleteTarget || !canDeleteUser(deleteTarget)) return
    setDeleting(true)
    try {
      await deleteUser(deleteTarget.id)
      await queryClient.invalidateQueries({ queryKey: ["users"] })
      toast({ title: "User deleted", description: deleteTarget.username })
      setDeleteTarget(null)
    } catch (e) {
      toast({
        title: "Delete failed",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setDeleting(false)
    }
  }

  const filteredUsers = users.filter((u) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      u.username.toLowerCase().includes(q) ||
      (u.full_name ?? "").toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      roleLabel(u.role).toLowerCase().includes(q) ||
      locationLabel(u.location).toLowerCase().includes(q)
    )
  })

  const activeCount = users.filter((u) => u.is_active).length

  return (
    <ModulePageLayout
      title="User & Role Management"
      description="Manage system users, roles, and permissions"
      breadcrumbs={[{ label: "Administration" }, { label: "Users & Roles" }]}
    >
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Users
              </CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{hasAuth ? users.length : "—"}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {hasAuth ? `${activeCount} active in database` : "Log in to load users"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Roles
              </CardTitle>
              <Shield className="h-4 w-4 text-[#3b82f6]" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{ROLE_OPTIONS.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Defined roles</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Storage
              </CardTitle>
              <UserPlus className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{hasAuth ? "API" : "—"}</div>
              <p className="text-xs text-muted-foreground mt-1">PostgreSQL / Django</p>
            </CardContent>
          </Card>
        </div>

        <Card className="w-full min-w-0">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <CardTitle>Users & Roles</CardTitle>
              <CardDescription>Assign roles and manage access</CardDescription>
            </div>
            <Button className="w-full bg-[#3b82f6] text-white hover:bg-[#2563eb] sm:w-auto" onClick={openAddForm}>
              <UserPlus className="h-4 w-4 mr-2" />
              Add User
            </Button>
          </CardHeader>
          <CardContent className="w-full min-w-0">
            {!hasAuth && (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mb-4">
                Sign in with an Admin or HR account to view and create users in the database.
              </p>
            )}
            {loadError && (
              <p className="text-sm text-destructive mb-4">
                {loadError instanceof Error ? loadError.message : "Failed to load users"}
              </p>
            )}
            <Tabs defaultValue="users" className="w-full">
              <TabsList>
                <TabsTrigger value="users">Users</TabsTrigger>
                <TabsTrigger value="roles">Roles</TabsTrigger>
              </TabsList>
              <TabsContent value="users" className="mt-6">
                <Input
                  placeholder="Search users..."
                  className="mb-4 w-full sm:w-64"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {isLoading ? (
                  <p className="text-sm text-muted-foreground py-8 flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading users…
                  </p>
                ) : (
                <div className="w-full max-w-full overflow-x-auto rounded-lg border pb-2">
                <Table className="min-w-[1000px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Username</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUsers.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                          {hasAuth ? "No users found." : "Sign in to see users."}
                        </TableCell>
                      </TableRow>
                    ) : (
                    filteredUsers.map((row: ApiUser) => (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium">
                          {row.full_name?.trim() || "—"}
                        </TableCell>
                        <TableCell>{row.username}</TableCell>
                        <TableCell className="text-muted-foreground">{row.email}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{roleLabel(row.role)}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {locationLabel(row.location)}
                        </TableCell>
                        <TableCell>
                          <Badge variant={row.is_active ? "default" : "secondary"}>
                            {row.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-[#3b82f6]"
                              onClick={() => openView(row)}
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              View
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-[#3b82f6]"
                              onClick={() => openEditForm(row)}
                            >
                              <Pencil className="h-4 w-4 mr-1" />
                              Edit
                            </Button>
                            {canDeleteUser(row) ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                                onClick={() => setDeleteTarget(row)}
                              >
                                <Trash2 className="h-4 w-4 mr-1" />
                                Delete
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled
                                title="Admin accounts cannot be deleted"
                              >
                                <Trash2 className="h-4 w-4 mr-1" />
                                Delete
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                    )}
                  </TableBody>
                </Table>
                </div>
                )}
              </TabsContent>
              <TabsContent value="roles" className="mt-6">
                <div className="w-full max-w-full overflow-x-auto rounded-lg border pb-2">
                <Table className="min-w-[760px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Role Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Users</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[
                      { name: "Super Admin", desc: "Full system access — all collectorates", role: "ADMIN" },
                      { name: "Location Administrator", desc: "Full access for one collectorate site", role: "LOCATION_ADMIN" },
                      { name: "Operation Manager", desc: "Operations oversight", role: "OPERATION_MANAGER" },
                      { name: "Inspector", desc: "Inspection and field ops", role: "INSPECTOR" },
                      { name: "Collector", desc: "Collectorate level access", role: "COLLECTOR" },
                      { name: "Deputy Collector", desc: "Deputy collectorate duties", role: "DEPUTY_COLLECTOR" },
                      { name: "Assistant Collector", desc: "Assistant collectorate duties", role: "ASSISTANT_COLLECTOR" },
                      { name: "Receptionist", desc: "Reception and front desk", role: "RECEPTIONIST" },
                      { name: "Guard", desc: "Gate check-in and reception panel only", role: "GUARD" },
                      { name: "Human Resource", desc: "HR module and personnel", role: "HR" },
                      { name: "Warehouse Officer", desc: "Warehouse and inventory", role: "WAREHOUSE_OFFICER" },
                      { name: "Detection Officer", desc: "Detection and enforcement", role: "DETECTION_OFFICER" },
                      { name: "FIR Officer", desc: "FIR registration and records", role: "FIR_OFFICER" },
                      { name: "Investigation Officer", desc: "Case investigation workflow", role: "INVESTIGATION_OFFICER" },
                      { name: "Seizing Officer", desc: "Seizure and custody operations", role: "SEIZING_OFFICER" },
                    ].map((row) => (
                      <TableRow key={row.role}>
                        <TableCell className="font-medium">{row.name}</TableCell>
                        <TableCell className="text-muted-foreground">{row.desc}</TableCell>
                        <TableCell>
                          {users.filter((u) => u.role === row.role).length}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" className="text-[#3b82f6]">
                            Permissions
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete user?</AlertDialogTitle>
            <AlertDialogDescription>
              Remove access for{" "}
              <strong>{deleteTarget?.full_name?.trim() || deleteTarget?.username}</strong>? Admin
              accounts cannot be deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleting}
              onClick={(e) => {
                e.preventDefault()
                void confirmDelete()
              }}
            >
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ModulePageLayout>
  )
}

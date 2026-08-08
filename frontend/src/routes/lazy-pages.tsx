/**
 * Lazy-loaded page components. One entry per screen.
 * Page names must match the "page" field in route-list.ts.
 */
import { lazy } from "react"

export const PAGES = {
  NotFound: lazy(() => import("@/pages/NotFound").then((m) => ({ default: m.NotFound }))),
  Login: lazy(() => import("@/pages/auth/login").then((m) => ({ default: m.default }))),
  Dashboard: lazy(() => import("@/pages/dashboard/Dashboard").then((m) => ({ default: m.Dashboard }))),
  VisitorManagementOverview: lazy(() => import("@/pages/vms/VisitorManagementOverview").then((m) => ({ default: m.VisitorManagementOverview }))),
  PreRegistration: lazy(() => import("@/pages/registration/PreRegistration").then((m) => ({ default: m.default }))),
  WalkInRegistration: lazy(() => import("@/pages/registration/WalkInRegistration").then((m) => ({ default: m.default }))),
  VisitorDetail: lazy(() => import("@/pages/registration/VisitorDetail").then((m) => ({ default: m.default }))),
  StreamedUpload: lazy(() => import("@/pages/registration/StreamedUpload").then((m) => ({ default: m.default }))),
  PhotoCapture: lazy(() => import("@/pages/registration/PhotoCapture").then((m) => ({ default: m.default }))),
  QRCodeGeneration: lazy(() => import("@/pages/registration/QRCodeGeneration").then((m) => ({ default: m.default }))),
  AppointmentScheduling: lazy(() => import("@/pages/registration/AppointmentScheduling").then((m) => ({ default: m.default }))),
  TimeSlotBooking: lazy(() => import("@/pages/registration/TimeSlotBooking").then((m) => ({ default: m.default }))),
  HostSelection: lazy(() => import("@/pages/registration/HostSelection").then((m) => ({ default: m.default }))),
  VisitPurpose: lazy(() => import("@/pages/registration/VisitPurpose").then((m) => ({ default: m.default }))),
  CalendarView: lazy(() => import("@/pages/registration/CalendarView").then((m) => ({ default: m.default }))),
  SecurityScreening: lazy(() => import("@/pages/registration/SecurityScreening").then((m) => ({ default: m.default }))),
  WatchlistScreening: lazy(() => import("@/pages/registration/WatchlistScreening").then((m) => ({ default: m.default }))),
  BlacklistManagement: lazy(() => import("@/pages/registration/BlacklistManagement").then((m) => ({ default: m.default }))),
  FlaggedVisitorAlerts: lazy(() => import("@/pages/registration/FlaggedVisitorAlerts").then((m) => ({ default: m.default }))),
  AccessControl: lazy(() => import("@/pages/registration/AccessControl").then((m) => ({ default: m.default }))),
  ZoneRestrictions: lazy(() => import("@/pages/registration/ZoneRestrictions").then((m) => ({ default: m.default }))),
  GateIntegration: lazy(() => import("@/pages/registration/GateIntegration").then((m) => ({ default: m.default }))),
  EscortRequirement: lazy(() => import("@/pages/registration/EscortRequirement").then((m) => ({ default: m.default }))),
  HostDepartmentDashboard: lazy(() => import("@/pages/registration/HostDepartmentDashboard").then((m) => ({ default: m.default }))),
  VisitorNotifications: lazy(() => import("@/pages/registration/VisitorNotifications").then((m) => ({ default: m.default }))),
  UpcomingVisits: lazy(() => import("@/pages/registration/UpcomingVisits").then((m) => ({ default: m.default }))),
  VisitorHistory: lazy(() => import("@/pages/registration/VisitorHistory").then((m) => ({ default: m.default }))),
  GuardReceptionPanel: lazy(() => import("@/pages/registration/GuardReceptionPanel").then((m) => ({ default: m.default }))),
  VehicleContractorManagement: lazy(() => import("@/pages/registration/VehicleContractorManagement").then((m) => ({ default: m.default }))),
  VehicleRegistration: lazy(() => import("@/pages/registration/VehicleRegistration").then((m) => ({ default: m.default }))),
  VehicleTracking: lazy(() => import("@/pages/registration/VehicleTracking").then((m) => ({ default: m.default }))),
  ContractorPasses: lazy(() => import("@/pages/registration/ContractorPasses").then((m) => ({ default: m.default }))),
  CargoDeliveryLogs: lazy(() => import("@/pages/registration/CargoDeliveryLogs").then((m) => ({ default: m.default }))),
  Armory: lazy(() => import("@/pages/armory/Armory").then((m) => ({ default: m.default }))),
  WarehouseSetup: lazy(() => import("@/pages/warehouse/WarehouseSetup").then((m) => ({ default: m.default }))),
  ZoneLocationManagement: lazy(() => import("@/pages/warehouse/ZoneLocationManagement").then((m) => ({ default: m.default }))),
  StorageAllocation: lazy(() => import("@/pages/warehouse/StorageAllocation").then((m) => ({ default: m.default }))),
  InventoryTracking: lazy(() => import("@/pages/warehouse/InventoryTracking").then((m) => ({ default: m.default }))),
  StockReconciliation: lazy(() => import("@/pages/warehouse/StockReconciliation").then((m) => ({ default: m.default }))),
  ReleaseInventory: lazy(() => import("@/pages/warehouse/ReleaseInventory").then((m) => ({ default: m.default }))),
  MemoDistribution: lazy(() => import("@/pages/warehouse/MemoDistribution").then((m) => ({ default: m.default }))),
  DestructionRecordDetail: lazy(() =>
    import("@/pages/warehouse/DestructionRecordDetail").then((m) => ({ default: m.default }))
  ),
  HSCodesFile: lazy(() => import("@/pages/warehouse/HSCodesFile").then((m) => ({ default: m.default }))),
  DepositAccountRegister: lazy(() => import("@/pages/warehouse/DepositAccountRegister").then((m) => ({ default: m.default }))),
  DepositAccountRegisterDetail: lazy(() =>
    import("@/pages/warehouse/DepositAccountRegisterDetail").then((m) => ({ default: m.default }))
  ),
  DetentionMemo: lazy(() => import("@/pages/detentions/DetentionMemo").then((m) => ({ default: m.default }))),
  DetentionMemoCreate: lazy(() => import("@/pages/detentions/DetentionMemoCreate").then((m) => ({ default: m.default }))),
  DetentionMemoDetail: lazy(() => import("@/pages/detentions/DetentionMemoDetail").then((m) => ({ default: m.default }))),
  SeizedInventory: lazy(() => import("@/pages/detentions/SeizedInventory").then((m) => ({ default: m.default }))),
  SeizedInventoryDetail: lazy(() => import("@/pages/detentions/SeizedInventoryDetail").then((m) => ({ default: m.default }))),
  GoodsReceipt: lazy(() => import("@/pages/inventory/GoodsReceipt").then((m) => ({ default: m.default }))),
  GoodsReceiptDetail: lazy(() => import("@/pages/inventory/GoodsReceiptDetail").then((m) => ({ default: m.default }))),
  StockManagement: lazy(() => import("@/pages/inventory/StockManagement").then((m) => ({ default: m.default }))),
  StockManagementDetail: lazy(() => import("@/pages/inventory/StockManagementDetail").then((m) => ({ default: m.default }))),
  CycleCountingAudit: lazy(() => import("@/pages/inventory/CycleCountingAudit").then((m) => ({ default: m.default }))),
  CycleCountingAuditDetail: lazy(() => import("@/pages/inventory/CycleCountingAuditDetail").then((m) => ({ default: m.default }))),
  InventoryValuation: lazy(() => import("@/pages/inventory/InventoryValuation").then((m) => ({ default: m.default }))),
  InventoryValuationDetail: lazy(() => import("@/pages/inventory/InventoryValuationDetail").then((m) => ({ default: m.default }))),
  CameraIntegration: lazy(() => import("@/pages/cameras/CameraIntegration").then((m) => ({ default: m.default }))),
  OperationsDashboard: lazy(() => import("@/pages/operations/OperationsDashboard").then((m) => ({ default: m.default }))),
  AnalyticsDashboard: lazy(() => import("@/pages/operations/AnalyticsDashboard").then((m) => ({ default: m.default }))),
  LiveCameraGrid: lazy(() => import("@/pages/operations/LiveCameraGrid").then((m) => ({ default: m.default }))),
  VehicleDetection: lazy(() => import("@/pages/operations/VehicleDetection").then((m) => ({ default: m.default }))),
  AiModels: lazy(() => import("@/pages/operations/AiModels").then((m) => ({ default: m.default }))),
  AiZones: lazy(() => import("@/pages/operations/AiZones").then((m) => ({ default: m.default }))),
  AiRules: lazy(() => import("@/pages/operations/AiRules").then((m) => ({ default: m.default }))),
  AiTraining: lazy(() => import("@/pages/operations/AiTraining").then((m) => ({ default: m.default }))),
  LiveMonitoring: lazy(() => import("@/pages/cameras/LiveMonitoring").then((m) => ({ default: m.default }))),
  NewSeizureEntry: lazy(() => import("@/pages/seizures/NewSeizureEntry").then((m) => ({ default: m.default }))),
  JcpTollPlazaEntry: lazy(() => import("@/pages/seizures/JcpTollPlazaEntry").then((m) => ({ default: m.default }))),
  GoodsReceiptHandover: lazy(() => import("@/pages/seizures/GoodsReceiptHandover").then((m) => ({ default: m.default }))),
  AiItemCataloging: lazy(() => import("@/pages/seizures/AiItemCataloging").then((m) => ({ default: m.default }))),
  SeizureRegister: lazy(() => import("@/pages/seizures/SeizureRegister").then((m) => ({ default: m.default }))),
  FirRegistration: lazy(() => import("@/pages/seizures/FirRegistration").then((m) => ({ default: m.default }))),
  CaseFileCreation: lazy(() => import("@/pages/seizures/CaseFileCreation").then((m) => ({ default: m.default }))),
  CourtProceedings: lazy(() => import("@/pages/seizures/CourtProceedings").then((m) => ({ default: m.default }))),
  LegalDocuments: lazy(() => import("@/pages/seizures/LegalDocuments").then((m) => ({ default: m.default }))),
  CaseStatusTracking: lazy(() => import("@/pages/seizures/CaseStatusTracking").then((m) => ({ default: m.default }))),
  SeizureManagementDashboard: lazy(() =>
    import("@/pages/seizure-management/SeizureManagementDashboard").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtNoteSheet: lazy(() =>
    import("@/pages/seizure-management/NoteSheet").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtNoteSheetCreate: lazy(() =>
    import("@/pages/seizure-management/NoteSheetCreate").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtNoteSheetEdit: lazy(() =>
    import("@/pages/seizure-management/NoteSheetCreate").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtNoteSheetDetail: lazy(() =>
    import("@/pages/seizure-management/NoteSheetDetail").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtAssessment: lazy(() =>
    import("@/pages/seizure-management/DetentionAssessment").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtAssessmentCreate: lazy(() =>
    import("@/pages/seizure-management/AssessmentCreate").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtAssessmentEdit: lazy(() =>
    import("@/pages/seizure-management/AssessmentCreate").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtAssessmentDetail: lazy(() =>
    import("@/pages/seizure-management/AssessmentDetail").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtDetentionReporting: lazy(() =>
    import("@/pages/seizure-management/DetentionReporting").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtRecoveryMemo: lazy(() =>
    import("@/pages/seizure-management/RecoveryMemo").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtRecoveryMemoCreate: lazy(() =>
    import("@/pages/seizure-management/RecoveryMemoCreate").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtRecoveryMemoDetail: lazy(() =>
    import("@/pages/seizure-management/RecoveryMemoDetail").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtRecoveryReporting: lazy(() =>
    import("@/pages/seizure-management/RecoveryReporting").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtSeizureReport: lazy(() =>
    import("@/pages/seizure-management/SeizureReport").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtSeizureReportCreate: lazy(() =>
    import("@/pages/seizure-management/SeizureReportCreate").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtSeizureReportDetail: lazy(() =>
    import("@/pages/seizure-management/SeizureReportDetail").then((m) => ({ default: m.default }))
  ),
  SeizureMgmtReports: lazy(() =>
    import("@/pages/seizure-management/SeizureManagementReports").then((m) => ({ default: m.default }))
  ),
  InterCollectorateTransfer: lazy(() => import("@/pages/transfers/InterCollectorateTransfer").then((m) => ({ default: m.default }))),
  InternalMovement: lazy(() => import("@/pages/transfers/InternalMovement").then((m) => ({ default: m.default }))),
  HandoverRequests: lazy(() => import("@/pages/transfers/HandoverRequests").then((m) => ({ default: m.default }))),
  DoubleAuthentication: lazy(() => import("@/pages/transfers/DoubleAuthentication").then((m) => ({ default: m.default }))),
  TransferTracking: lazy(() => import("@/pages/transfers/TransferTracking").then((m) => ({ default: m.default }))),
  PerishableRegister: lazy(() => import("@/pages/inventory/PerishableRegister").then((m) => ({ default: m.default }))),
  ExpiryTracking: lazy(() => import("@/pages/inventory/ExpiryTracking").then((m) => ({ default: m.default }))),
  PriorityDisposalQueue: lazy(() => import("@/pages/inventory/PriorityDisposalQueue").then((m) => ({ default: m.default }))),
  DestructionOrders: lazy(() => import("@/pages/inventory/DestructionOrders").then((m) => ({ default: m.default }))),
  LotCreation: lazy(() => import("@/pages/inventory/LotCreation").then((m) => ({ default: m.default }))),
  ItemValuation: lazy(() => import("@/pages/inventory/ItemValuation").then((m) => ({ default: m.default }))),
  AsoPortalSync: lazy(() => import("@/pages/auction/AsoPortalSync").then((m) => ({ default: m.default }))),
  BiddingManagement: lazy(() => import("@/pages/auction/BiddingManagement").then((m) => ({ default: m.default }))),
  SaleCompletion: lazy(() => import("@/pages/auction/SaleCompletion").then((m) => ({ default: m.default }))),
  RevenueReports: lazy(() => import("@/pages/auction/RevenueReports").then((m) => ({ default: m.default }))),
  CameraManagement: lazy(() => import("@/pages/cameras/CameraManagement").then((m) => ({ default: m.default }))),
  CameraManagementView: lazy(() => import("@/pages/cameras/CameraManagementView").then((m) => ({ default: m.default }))),
  CameraIntegrationView: lazy(() =>
    import("@/pages/cameras/CameraManagementView").then((m) => ({
      default: m.CameraIntegrationViewPage,
    }))
  ),
  AnalyticsCameraManagement: lazy(() => import("@/pages/cameras/AnalyticsCameraManagement").then((m) => ({ default: m.default }))),
  AnalyticsCameraManagementView: lazy(() =>
    import("@/pages/cameras/CameraManagementView").then((m) => ({
      default: m.AnalyticsCameraManagementViewPage,
    }))
  ),
  ObjectDetection: lazy(() => import("@/pages/cameras/ObjectDetection").then((m) => ({ default: m.default }))),
  PersonJourney: lazy(() => import("@/pages/operations/PersonJourney").then((m) => ({ default: m.default }))),
  PersonJourneyDetail: lazy(() =>
    import("@/pages/operations/PersonJourneyDetail").then((m) => ({ default: m.default }))
  ),
  AnprSettings: lazy(() => import("@/pages/cameras/AnprSettings").then((m) => ({ default: m.default }))),
  AnprVehicleTracking: lazy(() =>
    import("@/pages/cameras/VehicleTracking").then((m) => ({ default: m.default }))
  ),
  NumberPlateDetection: lazy(() =>
    import("@/pages/cameras/NumberPlateDetection").then((m) => ({ default: m.default }))
  ),
  AnomalyDetection: lazy(() => import("@/pages/cameras/AnomalyDetection").then((m) => ({ default: m.default }))),
  Reports: lazy(() => import("@/pages/reports/Reports").then((m) => ({ default: m.default }))),
  PredictiveInsights: lazy(() => import("@/pages/reports/PredictiveInsights").then((m) => ({ default: m.default }))),
  DataVisualization: lazy(() => import("@/pages/reports/DataVisualization").then((m) => ({ default: m.default }))),
  Employees: lazy(() => import("@/pages/hr/Employees").then((m) => ({ default: m.default }))),
  AddStaff: lazy(() => import("@/pages/hr/AddStaff").then((m) => ({ default: m.default }))),
  EmployeeDetail: lazy(() => import("@/pages/hr/EmployeeDetail").then((m) => ({ default: m.default }))),
  EmployeeEdit: lazy(() => import("@/pages/hr/EmployeeEdit").then((m) => ({ default: m.default }))),
  Attendance: lazy(() => import("@/pages/hr/Attendance").then((m) => ({ default: m.default }))),
  FaceEnrollment: lazy(() => import("@/pages/hr/FaceEnrollment").then((m) => ({ default: m.default }))),
  AttendanceMonitor: lazy(() => import("@/pages/hr/AttendanceMonitor").then((m) => ({ default: m.default }))),
  AttendanceDashboard: lazy(() => import("@/pages/hr/AttendanceDashboard").then((m) => ({ default: m.default }))),
  AttendanceReports: lazy(() => import("@/pages/hr/AttendanceReports").then((m) => ({ default: m.default }))),
  LeaveManagement: lazy(() => import("@/pages/hr/LeaveManagement").then((m) => ({ default: m.default }))),
  Payroll: lazy(() => import("@/pages/hr/Payroll").then((m) => ({ default: m.default }))),
  GeneralSettings: lazy(() => import("@/pages/settings/GeneralSettings").then((m) => ({ default: m.default }))),
  UserRoleManagement: lazy(() => import("@/pages/settings/UserRoleManagement").then((m) => ({ default: m.default }))),
  UserForm: lazy(() => import("@/pages/settings/UserFormPage").then((m) => ({ default: m.default }))),
  UserDetail: lazy(() => import("@/pages/settings/UserDetailPage").then((m) => ({ default: m.default }))),
  Integrations: lazy(() => import("@/pages/settings/Integrations").then((m) => ({ default: m.default }))),
  Notifications: lazy(() => import("@/pages/settings/Notifications").then((m) => ({ default: m.default }))),
  SecurityAccess: lazy(() => import("@/pages/settings/SecurityAccess").then((m) => ({ default: m.default }))),
  ActivityLogs: lazy(() => import("@/pages/settings/ActivityLogs").then((m) => ({ default: m.default }))),
  ActivityLogDetail: lazy(() => import("@/pages/settings/ActivityLogDetail").then((m) => ({ default: m.default }))),
  TableOfContents: lazy(() => import("@/pages/TableOfContents").then((m) => ({ default: m.default }))),
  PlaybackSearch: lazy(() => import("@/pages/operations/PlaybackSearch").then((m) => ({ default: m.default }))),
  ThermalImaging: lazy(() => import("@/pages/operations/ThermalImaging").then((m) => ({ default: m.default }))),
  AlertsNotifications: lazy(() => import("@/pages/operations/AlertsNotifications").then((m) => ({ default: m.default }))),
  IncidentManagement: lazy(() => import("@/pages/operations/IncidentManagement").then((m) => ({ default: m.default }))),
  AIIncidentManagement: lazy(() => import("@/pages/operations/AIIncidentManagement").then((m) => ({ default: m.default }))),
  ThermalAlerts: lazy(() => import("@/pages/operations/ThermalAlerts").then((m) => ({ default: m.default }))),
  AIDetectionAlerts: lazy(() => import("@/pages/operations/AIDetectionAlerts").then((m) => ({ default: m.default }))),
  ZoneAlerts: lazy(() => import("@/pages/operations/ZoneAlerts").then((m) => ({ default: m.default }))),
  SystemAlerts: lazy(() => import("@/pages/operations/SystemAlerts").then((m) => ({ default: m.default }))),
  PeopleDatabase: lazy(() => import("@/pages/operations/PeopleDatabase").then((m) => ({ default: m.default }))),
  PeopleDatabaseDetail: lazy(() => import("@/pages/operations/PeopleDatabaseDetail").then((m) => ({ default: m.default }))),
  VehicleDatabase: lazy(() => import("@/pages/operations/VehicleDatabase").then((m) => ({ default: m.default }))),
  MobileApp: lazy(() => import("@/pages/operations/MobileApp").then((m) => ({ default: m.default }))),
  DatabaseTables: lazy(() => import("@/pages/operations/DatabaseTables").then((m) => ({ default: m.default }))),
  VehicleDatabaseDetail: lazy(() => import("@/pages/operations/VehicleDatabaseDetail").then((m) => ({ default: m.default }))),
} as const
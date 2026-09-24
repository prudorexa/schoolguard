export interface Me {
  id: number
  email: string
  first_name: string
  last_name: string
  school_code: string | null
  is_super_admin: boolean
  roles: string[]
}

export interface RecentTransaction {
  type: "fee_payment" | "expense_paid"
  id: number
  amount: string
  date: string | null
  description: string
}

export interface FinancialSummary {
  total_collected: string
  total_expenses: string
  outstanding_fees: string
  net_position: string
  budget_allocated: string
  budget_spent: string
  budget_utilization_pct: string
  pending_expense_approvals: number
  recent_transactions: RecentTransaction[]
}

export interface FinancialAlert {
  severity: "critical" | "warning"
  category: string
  message: string
}

export interface AuditLogEntry {
  id: number
  user: number | null
  user_email: string | null
  action: string
  entity_type: string
  entity_id: number
  previous_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  reason: string
  ip_address: string | null
  created_at: string
}

export interface Department {
  id: number
  name: string
}

export interface ExpenseItem {
  id: number
  description: string
  amount: string
}

export type ExpenseStatus = "draft" | "pending_approval" | "approved" | "rejected" | "paid" | "cancelled"

export interface Expense {
  id: number
  title: string
  department: number
  department_name: string
  term: number | null
  supplier: number | null
  supplier_name: string | null
  amount: string
  status: ExpenseStatus
  items: ExpenseItem[]
  requested_by: number
  requested_by_email: string
  approved_by: number | null
  approved_by_email: string | null
  approved_at: string | null
  rejection_reason: string
  paid_at: string | null
  created_at: string
}

export interface Term {
  id: number
  academic_year: number
  name: string
  start_date: string
  end_date: string
  is_current: boolean
}

export interface FeeCategory {
  id: number
  name: string
}

export interface PurchaseRequestItem {
  id: number
  description: string
  quantity: number
  estimated_unit_price: string
  estimated_total: string
}

export type PurchaseRequestStatus = "draft" | "pending_approval" | "approved" | "rejected" | "converted" | "cancelled"

export interface PurchaseRequest {
  id: number
  title: string
  department: number
  department_name: string
  estimated_amount: string
  status: PurchaseRequestStatus
  items: PurchaseRequestItem[]
  requested_by: number
  requested_by_email: string
  approved_by: number | null
  approved_by_email: string | null
  approved_at: string | null
  rejection_reason: string
  has_purchase_order: boolean
  created_at: string
}

export interface Quotation {
  id: number
  purchase_request: number
  supplier: number
  supplier_name: string
  amount: string
  notes: string
  submitted_by_email: string
  created_at: string
}

export type PurchaseOrderStatus = "issued" | "delivered" | "cancelled"

export interface PurchaseOrder {
  id: number
  purchase_request: number
  purchase_request_title: string
  selected_quotation: number
  supplier: number
  supplier_name: string
  amount: string
  status: PurchaseOrderStatus
  issued_by_email: string
  issued_at: string
  has_delivery: boolean
  has_invoice: boolean
}

export interface Delivery {
  id: number
  purchase_order: number
  is_complete: boolean
  notes: string
  received_by_email: string
  delivered_at: string
}

export interface SupplierInvoice {
  id: number
  purchase_order: number
  invoice_number: string
  amount: string
  recorded_by_email: string
  received_at: string
}

export interface DiscrepancyReport {
  requested_amount: string
  po_amount: string
  invoiced_amount: string | null
  delivered: boolean
  flags: string[]
}

export interface AskAssistantResponse {
  answer: string
  tool_called: string
  data: Record<string, unknown>
}

export interface Budget {
  id: number
  term: number
  term_name: string
  department: number
  department_name: string
  allocated_amount: string
  warning_threshold_pct: string
  created_at: string
}

export interface BudgetStatus {
  budget_id: number
  department: string
  term: string
  allocated_amount: string
  spent_amount: string
  remaining_amount: string
  utilization_pct: string
  is_over_budget: boolean
  is_near_threshold: boolean
}

export interface Supplier {
  id: number
  name: string
  contact_person: string
  phone: string
  email: string
  tax_id: string
  status: "active" | "inactive"
  notes: string
  created_at: string
}

export interface SchoolClass {
  id: number
  name: string
}

export interface Student {
  id: number
  admission_number: string
  first_name: string
  last_name: string
  full_name: string
  date_of_birth: string | null
  school_class: number | null
  status: string
  created_at?: string
}

export interface InvoiceItem {
  id: number
  fee_category: number
  fee_category_name: string
  description: string
  amount: string
}

export type InvoiceStatus = "issued" | "partially_paid" | "paid" | "cancelled"

export interface Invoice {
  id: number
  student: number
  student_name: string
  term: number
  total_amount: string
  amount_paid: string
  balance: string
  status: InvoiceStatus
  items: InvoiceItem[]
  created_at: string
}

export type PaymentMethod = "mpesa" | "bank_transfer" | "cash" | "card" | "other"
export type PaymentStatus = "completed" | "reversed"

export interface Payment {
  id: number
  invoice: number
  amount: string
  method: PaymentMethod
  reference_number: string
  recorded_by: number
  recorded_by_email: string
  status: PaymentStatus
  reversal_reason: string
  receipt_number: string | null
  paid_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

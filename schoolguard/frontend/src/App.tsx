import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom"

import { AuditLogPage } from "./features/audit/AuditLogPage"
import { LoginPage } from "./features/auth/LoginPage"
import { AssistantPage } from "./features/assistant/AssistantPage"
import { NewBudgetPage } from "./features/budgets/NewBudgetPage"
import { BudgetsListPage } from "./features/budgets/BudgetsListPage"
import { DashboardPage } from "./features/dashboard/DashboardPage"
import { ExpenseDetailPage } from "./features/expenses/ExpenseDetailPage"
import { ExpensesListPage } from "./features/expenses/ExpensesListPage"
import { NewExpensePage } from "./features/expenses/NewExpensePage"
import { InvoiceDetailPage } from "./features/fees/InvoiceDetailPage"
import { InvoicesListPage } from "./features/fees/InvoicesListPage"
import { NewInvoicePage } from "./features/fees/NewInvoicePage"
import { NewPurchaseRequestPage } from "./features/procurement/NewPurchaseRequestPage"
import { PurchaseRequestDetailPage } from "./features/procurement/PurchaseRequestDetailPage"
import { PurchaseRequestsListPage } from "./features/procurement/PurchaseRequestsListPage"
import { NewStudentPage } from "./features/students/NewStudentPage"
import { StudentsListPage } from "./features/students/StudentsListPage"
import { NewSupplierPage } from "./features/suppliers/NewSupplierPage"
import { SuppliersListPage } from "./features/suppliers/SuppliersListPage"
import { useAuth } from "./lib/auth"

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-text-muted">Loading…</div>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit-log"
          element={
            <ProtectedRoute>
              <AuditLogPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/assistant"
          element={
            <ProtectedRoute>
              <AssistantPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/expenses"
          element={
            <ProtectedRoute>
              <ExpensesListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/expenses/new"
          element={
            <ProtectedRoute>
              <NewExpensePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/expenses/:id"
          element={
            <ProtectedRoute>
              <ExpenseDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/fees"
          element={
            <ProtectedRoute>
              <InvoicesListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/fees/new"
          element={
            <ProtectedRoute>
              <NewInvoicePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/fees/:id"
          element={
            <ProtectedRoute>
              <InvoiceDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/students"
          element={
            <ProtectedRoute>
              <StudentsListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/students/new"
          element={
            <ProtectedRoute>
              <NewStudentPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/suppliers"
          element={
            <ProtectedRoute>
              <SuppliersListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/suppliers/new"
          element={
            <ProtectedRoute>
              <NewSupplierPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/budgets"
          element={
            <ProtectedRoute>
              <BudgetsListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/budgets/new"
          element={
            <ProtectedRoute>
              <NewBudgetPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/procurement"
          element={
            <ProtectedRoute>
              <PurchaseRequestsListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/procurement/new"
          element={
            <ProtectedRoute>
              <NewPurchaseRequestPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/procurement/:id"
          element={
            <ProtectedRoute>
              <PurchaseRequestDetailPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

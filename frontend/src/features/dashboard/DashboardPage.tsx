import { AppShell } from "../../app/AppShell"
import { formatKes } from "../../lib/format"
import { AlertsList } from "./AlertsList"
import { RecentTransactionsList } from "./RecentTransactionsList"
import { StatBlock } from "./StatBlock"
import { useFinancialAlerts, useFinancialSummary } from "./useDashboard"

export function DashboardPage() {
  const summaryQuery = useFinancialSummary()
  const alertsQuery = useFinancialAlerts()

  return (
    <AppShell title="Dashboard">
      {summaryQuery.isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {summaryQuery.isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">Could not load the financial summary.</p>
      )}

      {summaryQuery.data && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatBlock label="Collected" value={formatKes(summaryQuery.data.total_collected)} tone="ledger" />
          <StatBlock label="Expenses" value={formatKes(summaryQuery.data.total_expenses)} />
          <StatBlock label="Outstanding fees" value={formatKes(summaryQuery.data.outstanding_fees)} tone="amber" />
          <StatBlock label="Budget utilization" value={`${summaryQuery.data.budget_utilization_pct}%`} />
        </div>
      )}

      <section className="mt-10">
        <h2 className="font-display text-lg font-medium text-text-primary">Financial Control Center</h2>
        <p className="mt-1 text-sm text-text-muted">Items flagged for review. Nothing here is decided automatically.</p>
        <div className="mt-4">
          {alertsQuery.isPending && <p className="text-sm text-text-muted">Loading…</p>}
          {alertsQuery.data && <AlertsList alerts={alertsQuery.data} />}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="font-display text-lg font-medium text-text-primary">Recent transactions</h2>
        <div className="mt-4">
          {summaryQuery.data && <RecentTransactionsList transactions={summaryQuery.data.recent_transactions} />}
        </div>
      </section>
    </AppShell>
  )
}

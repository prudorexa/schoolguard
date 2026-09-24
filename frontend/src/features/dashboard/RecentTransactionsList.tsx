import type { RecentTransaction } from "../../types/api"
import { formatDateTime, formatKes } from "../../lib/format"

export function RecentTransactionsList({ transactions }: { transactions: RecentTransaction[] }) {
  if (transactions.length === 0) {
    return (
      <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
        No transactions recorded yet.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-line rounded border border-line bg-surface">
      {transactions.map((txn) => {
        const isIncoming = txn.type === "fee_payment"
        return (
          <li key={`${txn.type}-${txn.id}`} className="flex items-center justify-between px-5 py-3.5">
            <div>
              <p className="text-sm text-text-primary">{txn.description}</p>
              <p className="mt-0.5 text-xs text-text-muted">{formatDateTime(txn.date)}</p>
            </div>
            <p className={`font-display text-base tabular-nums ${isIncoming ? "text-ledger" : "text-text-primary"}`}>
              {isIncoming ? "+" : "−"}
              {formatKes(txn.amount)}
            </p>
          </li>
        )
      })}
    </ul>
  )
}

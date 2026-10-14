import { useQuery } from "@tanstack/react-query"

import { AppShell } from "../../app/AppShell"
import { api } from "../../lib/api"
import { formatDateTime } from "../../lib/format"
import type { AuditLogEntry, PaginatedResponse } from "../../types/api"

export function AuditLogPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<AuditLogEntry>>("/audit-logs/")
      return data
    },
  })

  return (
    <AppShell title="Audit Log">
      <p className="mb-6 text-sm text-text-muted">
        Every sensitive change, in order. This list is read-only — corrections happen by reversal, never by editing
        history.
      </p>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && <p className="border-l-2 border-red pl-3 text-sm text-red">You don't have permission to view the audit log, or it could not be loaded.</p>}

      {data && data.results.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No audit entries yet.
        </div>
      )}

      {data && data.results.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.results.map((entry) => (
            <li key={entry.id} className="px-5 py-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text-primary">{entry.action}</p>
                <p className="text-xs text-text-muted">{formatDateTime(entry.created_at)}</p>
              </div>
              <p className="mt-1 text-xs text-text-muted">
                {entry.entity_type} #{entry.entity_id} · {entry.user_email ?? "system"}
              </p>
              {entry.reason && <p className="mt-2 text-sm text-text-primary">Reason: {entry.reason}</p>}
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}

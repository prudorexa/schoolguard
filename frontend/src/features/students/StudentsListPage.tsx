import { Plus } from "lucide-react"
import { Link } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useStudentsList } from "./useStudents"

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  inactive: "Inactive",
  graduated: "Graduated",
  transferred: "Transferred",
}

export function StudentsListPage() {
  const { data, isPending, isError } = useStudentsList()

  return (
    <AppShell title="Students">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-text-muted">Identified by admission number, not name.</p>
        <Link
          to="/students/new"
          className="flex items-center gap-1.5 rounded bg-ink px-3.5 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft"
        >
          <Plus className="h-4 w-4" />
          New student
        </Link>
      </div>

      {isPending && <p className="text-sm text-text-muted">Loading…</p>}
      {isError && (
        <p className="border-l-2 border-red pl-3 text-sm text-red">
          You don't have permission to view students, or they could not be loaded.
        </p>
      )}

      {data && data.length === 0 && (
        <div className="rounded border border-line bg-surface px-5 py-6 text-center text-sm text-text-muted">
          No students registered yet.
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-surface">
          {data.map((student) => (
            <li key={student.id} className="flex items-center justify-between px-5 py-3.5">
              <div>
                <p className="text-sm font-medium text-text-primary">{student.full_name}</p>
                <p className="mt-0.5 text-xs text-text-muted">Adm. No. {student.admission_number}</p>
              </div>
              <span className={`text-xs font-medium ${student.status === "active" ? "text-ledger" : "text-text-muted"}`}>
                {STATUS_LABELS[student.status] ?? student.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}

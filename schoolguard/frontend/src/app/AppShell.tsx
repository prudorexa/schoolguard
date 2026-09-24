import { ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'

/**
 * Minimal shell for Phase 1. The real sidebar (role-aware nav, active
 * school switcher, notifications) gets built once auth + schools exist —
 * this just establishes the visual language: neutral, dense, fintech,
 * not a "school website."
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-6 py-4">
          <ShieldCheck className="h-6 w-6 text-slate-900" />
          <span className="text-lg font-semibold tracking-tight text-slate-900">SchoolGuard</span>
          <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
            Phase 1 · Foundation
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  )
}

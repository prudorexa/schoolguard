import type { ReactNode } from "react"

import { Sidebar } from "./Sidebar"

export function AppShell({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="flex min-h-screen bg-paper">
      <Sidebar />
      <div className="flex-1">
        <header className="border-b border-line bg-surface px-8 py-5">
          <h1 className="font-display text-xl font-medium text-text-primary">{title}</h1>
        </header>
        <main className="px-8 py-8">{children}</main>
      </div>
    </div>
  )
}

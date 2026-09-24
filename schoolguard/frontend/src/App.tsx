import { AppShell } from './app/AppShell'
import { ScaffoldStatus } from './features/dashboard/ScaffoldStatus'

export default function App() {
  return (
    <AppShell>
      <div className="grid gap-6 sm:grid-cols-2">
        <ScaffoldStatus />
      </div>
    </AppShell>
  )
}

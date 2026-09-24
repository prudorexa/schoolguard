import { useHealth } from './useHealth'

export function ScaffoldStatus() {
  const { data, isPending, isError } = useHealth()

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-medium text-slate-500">Backend connectivity</h2>
      <div className="mt-2 flex items-center gap-2">
        {isPending && <StatusDot color="bg-amber-400" />}
        {isError && <StatusDot color="bg-red-500" />}
        {data && <StatusDot color="bg-emerald-500" />}
        <span className="text-lg font-semibold text-slate-900">
          {isPending && 'Checking...'}
          {isError && 'Unreachable — is `manage.py runserver` running?'}
          {data && `${data.service} — ${data.status}`}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-500">
        This card calls <code className="rounded bg-slate-100 px-1 py-0.5">GET /api/v1/health/</code> through the
        Vite dev proxy to confirm the frontend, Vite proxy, and Django backend are wired correctly before any real
        feature is built on top.
      </p>
    </div>
  )
}

function StatusDot({ color }: { color: string }) {
  return <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
}

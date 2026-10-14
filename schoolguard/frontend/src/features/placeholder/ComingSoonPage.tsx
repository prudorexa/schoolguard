import { AppShell } from "../../app/AppShell"

/**
 * Honest placeholder, not fake data -- these modules have full, tested
 * backend APIs (see the backend README) but no frontend built against
 * them yet. Each is a natural next feature-folder to build out.
 */
export function ComingSoonPage({ title }: { title: string }) {
  return (
    <AppShell title={title}>
      <div className="rounded border border-line bg-surface px-6 py-10 text-center">
        <p className="font-display text-lg text-text-primary">Not built yet</p>
        <p className="mt-2 text-sm text-text-muted">
          The {title.toLowerCase()} API is complete and tested on the backend -- this screen just hasn't been wired
          up yet.
        </p>
      </div>
    </AppShell>
  )
}

export function StatBlock({
  label,
  value,
  tone = "neutral",
}: {
  label: string
  value: string
  tone?: "neutral" | "ledger" | "amber" | "red"
}) {
  const toneClasses = {
    neutral: "bg-surface border-line",
    ledger: "bg-ledger-soft border-ledger/20",
    amber: "bg-amber-soft border-amber/20",
    red: "bg-red-soft border-red/20",
  }[tone]

  return (
    <div className={`rounded border px-5 py-4 ${toneClasses}`}>
      <p className="text-xs font-medium text-text-muted">{label}</p>
      <p className="mt-1 font-display text-3xl font-medium tabular-nums text-text-primary">{value}</p>
    </div>
  )
}

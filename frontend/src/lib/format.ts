export function formatKes(value: string | number): string {
  const num = typeof value === "string" ? Number(value) : value
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 0,
  }).format(num)
}

export function formatDate(value: string | null): string {
  if (!value) return "—"
  return new Intl.DateTimeFormat("en-KE", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value))
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—"
  return new Intl.DateTimeFormat("en-KE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    new Date(value),
  )
}

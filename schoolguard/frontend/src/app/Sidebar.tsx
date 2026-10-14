import {
  LayoutDashboard,
  Users,
  Receipt,
  Wallet,
  ShoppingCart,
  Building2,
  PiggyBank,
  ScrollText,
  ShieldCheck,
  Sparkles,
} from "lucide-react"
import { NavLink } from "react-router-dom"

import { useAuth } from "../lib/auth"

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/students", label: "Students", icon: Users },
  { to: "/fees", label: "Fees", icon: Receipt },
  { to: "/expenses", label: "Expenses", icon: Wallet },
  { to: "/procurement", label: "Procurement", icon: ShoppingCart },
  { to: "/suppliers", label: "Suppliers", icon: Building2 },
  { to: "/budgets", label: "Budgets", icon: PiggyBank },
  { to: "/audit-log", label: "Audit Log", icon: ScrollText },
  { to: "/assistant", label: "AI Assistant", icon: Sparkles },
]

export function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-ink text-text-inverse">
      <div className="flex items-center gap-2 px-5 py-5">
        <ShieldCheck className="h-5 w-5 text-ledger" />
        <span className="font-display text-lg font-semibold">SchoolGuard</span>
      </div>

      <nav className="mt-2 flex-1 space-y-0.5 px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-3 py-2 text-sm transition ${
                isActive ? "bg-ink-soft text-text-inverse" : "text-text-inverse/70 hover:bg-ink-soft hover:text-text-inverse"
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 px-5 py-4">
        <p className="truncate text-sm text-text-inverse">{user?.email}</p>
        <p className="mt-0.5 text-xs text-text-inverse/50">{user?.roles.join(", ") || "No role assigned"}</p>
        <button onClick={logout} className="mt-3 text-xs text-text-inverse/70 underline decoration-white/30 hover:text-text-inverse">
          Sign out
        </button>
      </div>
    </aside>
  )
}

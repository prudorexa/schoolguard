import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { ShieldCheck } from "lucide-react"

import { useAuth } from "../../lib/auth"

/**
 * Previously every failure -- wrong password, backend unreachable, proxy
 * misconfigured -- showed the same "Incorrect email or password" message.
 * That's actively misleading when the real problem is that the backend
 * simply isn't running: the person would go second-guess their password
 * when there's nothing wrong with it. Distinguish "no response at all"
 * (network/connection failure) from "got a response, credentials rejected."
 */
function loginErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number }; request?: unknown; message?: string }
  if (anyErr?.response?.status === 401) return "Incorrect email or password."
  if (anyErr?.request && !anyErr?.response) {
    return "Could not reach the server. Is the backend running?"
  }
  return "Something went wrong. Please try again."
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate("/", { replace: true })
    } catch (err) {
      setError(loginErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="flex w-full flex-col justify-center px-8 sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="mb-10 flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-ledger" />
          <span className="font-display text-xl font-semibold text-text-primary">SchoolGuard</span>
        </div>

        <h1 className="font-display text-2xl font-medium text-text-primary">Sign in</h1>
        <p className="mt-1 text-sm text-text-muted">Every shilling, traceable and accounted for.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-text-primary">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-text-primary">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
          </div>

          {error && (
            <p role="alert" className="border-l-2 border-red pl-3 text-sm text-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded bg-ink py-2.5 text-sm font-medium text-text-inverse transition hover:bg-ink-soft disabled:opacity-60"
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  )
}

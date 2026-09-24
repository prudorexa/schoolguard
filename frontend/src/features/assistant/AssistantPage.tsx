import { Sparkles } from "lucide-react"
import { useState, type FormEvent } from "react"

import { AppShell } from "../../app/AppShell"
import { assistantErrorMessage, useAskAssistant } from "./useAssistant"

interface ChatTurn {
  question: string
  answer?: string
  toolCalled?: string
  error?: string
  isNotConfigured?: boolean
}

const SUGGESTED_QUESTIONS = [
  "What's our overall financial position right now?",
  "Which expenses are awaiting approval?",
  "What are the five largest expenses this term?",
]

export function AssistantPage() {
  const [question, setQuestion] = useState("")
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const ask = useAskAssistant()

  async function handleAsk(q: string) {
    const trimmed = q.trim()
    if (!trimmed) return

    const turnIndex = turns.length
    setTurns((prev) => [...prev, { question: trimmed }])
    setQuestion("")

    try {
      const result = await ask.mutateAsync(trimmed)
      setTurns((prev) =>
        prev.map((t, i) => (i === turnIndex ? { ...t, answer: result.answer, toolCalled: result.tool_called } : t)),
      )
    } catch (err) {
      const { message, isNotConfigured } = assistantErrorMessage(err)
      setTurns((prev) => prev.map((t, idx) => (idx === turnIndex ? { ...t, error: message, isNotConfigured } : t)))
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    handleAsk(question)
  }

  return (
    <AppShell title="AI Assistant">
      <div className="mx-auto max-w-2xl">
        <p className="mb-6 text-sm text-text-muted">
          Answers are grounded in your school's real data only — never invented figures. Every question is logged.
        </p>

        {turns.length === 0 && (
          <div className="rounded border border-line bg-surface px-5 py-8 text-center">
            <Sparkles className="mx-auto h-5 w-5 text-ledger" />
            <p className="mt-3 text-sm text-text-muted">Ask something about your school's finances.</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleAsk(q)}
                  className="rounded-full border border-line bg-paper px-3 py-1.5 text-xs text-text-primary hover:border-ledger hover:text-ledger"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-5">
          {turns.map((turn, i) => (
            <div key={i}>
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-lg bg-ink px-4 py-2.5 text-sm text-text-inverse">{turn.question}</div>
              </div>

              {turn.answer && (
                <div className="mt-2 flex justify-start">
                  <div className="max-w-[85%] rounded-lg border border-line bg-surface px-4 py-2.5">
                    <p className="text-sm text-text-primary">{turn.answer}</p>
                    {turn.toolCalled && (
                      <p className="mt-1.5 text-xs text-text-muted">Grounded in: {turn.toolCalled}</p>
                    )}
                  </div>
                </div>
              )}

              {turn.error && (
                <div className="mt-2 flex justify-start">
                  <div
                    className={`max-w-[85%] rounded-lg border px-4 py-2.5 text-sm ${
                      turn.isNotConfigured ? "border-amber/30 bg-amber-soft text-text-primary" : "border-red/30 bg-red-soft text-text-primary"
                    }`}
                  >
                    {turn.error}
                    {turn.isNotConfigured && (
                      <p className="mt-1 text-xs text-text-muted">
                        An administrator needs to add an ANTHROPIC_API_KEY to the backend to enable this feature.
                      </p>
                    )}
                  </div>
                </div>
              )}

              {ask.isPending && i === turns.length - 1 && !turn.answer && !turn.error && (
                <div className="mt-2 flex justify-start">
                  <div className="rounded-lg border border-line bg-surface px-4 py-2.5 text-sm text-text-muted">
                    Thinking…
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about fees, expenses, budgets…"
            className="flex-1 rounded border border-line bg-surface px-3 py-2.5 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          />
          <button
            type="submit"
            disabled={ask.isPending || !question.trim()}
            className="rounded bg-ink px-4 py-2.5 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
          >
            Ask
          </button>
        </form>
      </div>
    </AppShell>
  )
}

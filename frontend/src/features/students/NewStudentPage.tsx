import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../../app/AppShell"
import { useClasses, useCreateStudent } from "./useStudents"

function apiErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  if (anyErr?.response?.status === 403) return "You do not have permission to do this."
  const data = anyErr?.response?.data
  if (data && typeof data === "object") {
    const obj = data as { admission_number?: string[] }
    if (obj.admission_number?.length) return obj.admission_number[0]
  }
  return "Could not create the student. Check that all fields are filled in correctly."
}

export function NewStudentPage() {
  const navigate = useNavigate()
  const classesQuery = useClasses()
  const createStudent = useCreateStudent()

  const [admissionNumber, setAdmissionNumber] = useState("")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [classId, setClassId] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const student = await createStudent.mutateAsync({
        admission_number: admissionNumber,
        first_name: firstName,
        last_name: lastName,
        school_class: classId ? Number(classId) : null,
      })
      navigate("/students", { state: { createdId: student.id } })
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <AppShell title="New student">
      <form onSubmit={handleSubmit} className="max-w-md space-y-5">
        <div>
          <label htmlFor="admission_number" className="block text-sm font-medium text-text-primary">
            Admission number
          </label>
          <input
            id="admission_number"
            required
            value={admissionNumber}
            onChange={(e) => setAdmissionNumber(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="first_name" className="block text-sm font-medium text-text-primary">
              First name
            </label>
            <input
              id="first_name"
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
          </div>
          <div>
            <label htmlFor="last_name" className="block text-sm font-medium text-text-primary">
              Last name
            </label>
            <input
              id="last_name"
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
            />
          </div>
        </div>

        <div>
          <label htmlFor="class" className="block text-sm font-medium text-text-primary">
            Class <span className="font-normal text-text-muted">(optional)</span>
          </label>
          <select
            id="class"
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
            className="mt-1.5 block w-full rounded border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-ledger focus:ring-1 focus:ring-ledger"
          >
            <option value="">No class assigned</option>
            {classesQuery.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="border-l-2 border-red pl-3 text-sm text-red">{error}</p>}

        <button
          type="submit"
          disabled={createStudent.isPending}
          className="rounded bg-ink px-4 py-2 text-sm font-medium text-text-inverse hover:bg-ink-soft disabled:opacity-60"
        >
          {createStudent.isPending ? "Saving…" : "Add student"}
        </button>
      </form>
    </AppShell>
  )
}

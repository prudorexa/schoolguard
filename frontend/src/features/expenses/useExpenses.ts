import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { Department, Expense, PaginatedResponse } from "../../types/api"

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Department>>("/departments/")
      return data.results
    },
  })
}

export function useExpenses() {
  return useQuery({
    queryKey: ["expenses"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Expense>>("/expenses/")
      return data.results
    },
  })
}

export function useExpense(id: string) {
  return useQuery({
    queryKey: ["expenses", id],
    queryFn: async () => {
      const { data } = await api.get<Expense>(`/expenses/${id}/`)
      return data
    },
  })
}

interface CreateExpenseInput {
  title: string
  department: number
  items: { description: string; amount: string }[]
}

export function useCreateExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateExpenseInput) => {
      const { data } = await api.post<Expense>("/expenses/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["expenses"] }),
  })
}

function useExpenseAction(action: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload?: Record<string, string> }) => {
      const { data } = await api.post<Expense>(`/expenses/${id}/${action}/`, payload ?? {})
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] })
      queryClient.setQueryData(["expenses", String(data.id)], data)
    },
  })
}

export function useSubmitExpense() {
  return useExpenseAction("submit")
}
export function useApproveExpense() {
  return useExpenseAction("approve")
}
export function useRejectExpense() {
  return useExpenseAction("reject")
}
export function useMarkExpensePaid() {
  return useExpenseAction("mark-paid")
}
export function useCancelExpense() {
  return useExpenseAction("cancel")
}

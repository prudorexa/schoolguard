import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { Budget, BudgetStatus, Department, PaginatedResponse, Term } from "../../types/api"

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Department>>("/departments/")
      return data.results
    },
  })
}

export function useTerms() {
  return useQuery({
    queryKey: ["terms"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Term>>("/terms/")
      return data.results
    },
  })
}

export function useBudgets() {
  return useQuery({
    queryKey: ["budgets"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Budget>>("/budgets/")
      return data.results
    },
  })
}

export function useBudgetStatus(id: number) {
  return useQuery({
    queryKey: ["budgets", id, "status"],
    queryFn: async () => {
      const { data } = await api.get<BudgetStatus>(`/budgets/${id}/status/`)
      return data
    },
  })
}

interface CreateBudgetInput {
  term: number
  department: number
  allocated_amount: string
}

export function useCreateBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateBudgetInput) => {
      const { data } = await api.post<Budget>("/budgets/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["budgets"] }),
  })
}

import { useQuery } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { FinancialAlert, FinancialSummary } from "../../types/api"

export function useFinancialSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: async () => {
      const { data } = await api.get<FinancialSummary>("/dashboard/summary/")
      return data
    },
  })
}

export function useFinancialAlerts() {
  return useQuery({
    queryKey: ["dashboard", "alerts"],
    queryFn: async () => {
      const { data } = await api.get<FinancialAlert[]>("/dashboard/alerts/")
      return data
    },
  })
}

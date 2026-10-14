import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { FeeCategory, Invoice, PaginatedResponse, Payment, PaymentMethod, Student, Term } from "../../types/api"

export function useTerms() {
  return useQuery({
    queryKey: ["terms"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Term>>("/terms/")
      return data.results
    },
  })
}

export function useStudents() {
  return useQuery({
    queryKey: ["students"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Student>>("/students/")
      return data.results
    },
  })
}

export function useFeeCategories() {
  return useQuery({
    queryKey: ["fee-categories"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<FeeCategory>>("/fee-categories/")
      return data.results
    },
  })
}

export function useInvoices() {
  return useQuery({
    queryKey: ["invoices"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Invoice>>("/invoices/")
      return data.results
    },
  })
}

export function useInvoice(id: string) {
  return useQuery({
    queryKey: ["invoices", id],
    queryFn: async () => {
      const { data } = await api.get<Invoice>(`/invoices/${id}/`)
      return data
    },
  })
}

interface CreateInvoiceInput {
  student: number
  term: number
  items: { fee_category_id: number; description: string; amount: string }[]
}

export function useCreateInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateInvoiceInput) => {
      const { data } = await api.post<Invoice>("/invoices/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invoices"] }),
  })
}

interface RecordPaymentInput {
  invoice: number
  amount: string
  method: PaymentMethod
  reference_number?: string
}

export function useRecordPayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: RecordPaymentInput) => {
      const { data } = await api.post<Payment>("/payments/", input)
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] })
      queryClient.invalidateQueries({ queryKey: ["invoices", String(variables.invoice)] })
    },
  })
}

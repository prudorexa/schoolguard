import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { PaginatedResponse, Supplier } from "../../types/api"

export function useSuppliers() {
  return useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Supplier>>("/suppliers/")
      return data.results
    },
  })
}

interface CreateSupplierInput {
  name: string
  contact_person?: string
  phone?: string
  email?: string
  tax_id?: string
}

export function useCreateSupplier() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateSupplierInput) => {
      const { data } = await api.post<Supplier>("/suppliers/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
  })
}

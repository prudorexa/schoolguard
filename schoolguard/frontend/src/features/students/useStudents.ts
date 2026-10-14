import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { PaginatedResponse, SchoolClass, Student } from "../../types/api"

export function useClasses() {
  return useQuery({
    queryKey: ["classes"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<SchoolClass>>("/classes/")
      return data.results
    },
  })
}

export function useStudentsList() {
  return useQuery({
    queryKey: ["students"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Student>>("/students/")
      return data.results
    },
  })
}

interface CreateStudentInput {
  admission_number: string
  first_name: string
  last_name: string
  school_class?: number | null
}

export function useCreateStudent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateStudentInput) => {
      const { data } = await api.post<Student>("/students/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["students"] }),
  })
}

import { useMutation } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type { AskAssistantResponse } from "../../types/api"

export function useAskAssistant() {
  return useMutation({
    mutationFn: async (question: string) => {
      const { data } = await api.post<AskAssistantResponse>("/ai/ask/", { question })
      return data
    },
  })
}

export function assistantErrorMessage(err: unknown): { message: string; isNotConfigured: boolean } {
  const anyErr = err as { response?: { status?: number; data?: unknown } }
  const status = anyErr?.response?.status

  if (status === 403) {
    return { message: "You don't have permission to use the AI assistant.", isNotConfigured: false }
  }
  if (status === 503) {
    const data = anyErr?.response?.data as { detail?: string } | undefined
    return {
      message: data?.detail ?? "The AI assistant isn't configured yet.",
      isNotConfigured: true,
    }
  }
  return { message: "Something went wrong asking that question. Please try again.", isNotConfigured: false }
}

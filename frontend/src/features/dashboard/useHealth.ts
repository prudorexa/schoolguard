import { useQuery } from '@tanstack/react-query'

import { api } from '../../lib/api'

interface HealthResponse {
  status: string
  service: string
}

async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health/')
  return data
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })
}

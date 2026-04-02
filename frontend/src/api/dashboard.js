import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => apiClient.get('/dashboard/summary').then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}

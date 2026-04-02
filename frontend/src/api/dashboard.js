import { useQuery } from '@tanstack/react-query'
import { useApiClient } from './client'

export function useDashboardSummary() {
  const api = useApiClient()
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => api.get('/dashboard/summary').then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}

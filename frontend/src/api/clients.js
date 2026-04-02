import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApiClient } from './client'

export function useClients() {
  const api = useApiClient()
  return useQuery({
    queryKey: ['clients'],
    queryFn: () => api.get('/clients').then((r) => r.data),
  })
}

export function useClient(id) {
  const api = useApiClient()
  return useQuery({
    queryKey: ['clients', id],
    queryFn: () => api.get(`/clients/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateClient() {
  const api = useApiClient()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => api.post('/clients', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clients'] }),
  })
}

export function useUpdateClient() {
  const api = useApiClient()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => api.put(`/clients/${id}`, data).then((r) => r.data),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['clients', id] }),
  })
}

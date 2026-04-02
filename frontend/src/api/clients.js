import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'

export function useClients() {
  return useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.get('/clients').then((r) => r.data),
  })
}

export function useClient(id) {
  return useQuery({
    queryKey: ['clients', id],
    queryFn: () => apiClient.get(`/clients/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => apiClient.post('/clients', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clients'] }),
  })
}

export function useUpdateClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => apiClient.put(`/clients/${id}`, data).then((r) => r.data),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['clients', id] }),
  })
}

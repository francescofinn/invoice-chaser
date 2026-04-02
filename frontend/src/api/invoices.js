import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApiClient } from './client'
import publicClient from './client'

export function useInvoices(status) {
  const api = useApiClient()
  return useQuery({
    queryKey: ['invoices', status ?? 'all'],
    queryFn: () =>
      api.get('/invoices', { params: status ? { status } : {} }).then((r) => r.data),
  })
}

export function useInvoice(id) {
  const api = useApiClient()
  return useQuery({
    queryKey: ['invoices', id],
    queryFn: () => api.get(`/invoices/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

// Public — no auth. Uses publicClient directly (not a hook dependency).
export function usePublicInvoice(token) {
  return useQuery({
    queryKey: ['invoices', 'public', token],
    queryFn: () => publicClient.get(`/invoices/public/${token}`).then((r) => r.data),
    enabled: !!token,
    // Poll every 5s so the page updates when the webhook fires after payment
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ['paid', 'partially_paid'].includes(status) ? false : 5_000
    },
  })
}

export function useCreateInvoice() {
  const api = useApiClient()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => api.post('/invoices', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useUpdateInvoice() {
  const api = useApiClient()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => api.put(`/invoices/${id}`, data).then((r) => r.data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['invoices', id] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

export function useDeleteInvoice() {
  const api = useApiClient()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => api.delete(`/invoices/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useSendInvoice() {
  const api = useApiClient()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => api.post(`/invoices/${id}/send`).then((r) => r.data),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['invoices', id] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

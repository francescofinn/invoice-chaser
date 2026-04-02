import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'

export function useInvoices(status) {
  return useQuery({
    queryKey: ['invoices', status ?? 'all'],
    queryFn: () =>
      apiClient.get('/invoices', { params: status ? { status } : {} }).then((r) => r.data),
  })
}

export function useInvoice(id) {
  return useQuery({
    queryKey: ['invoices', id],
    queryFn: () => apiClient.get(`/invoices/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function usePublicInvoice(token) {
  return useQuery({
    queryKey: ['invoices', 'public', token],
    queryFn: () => apiClient.get(`/invoices/public/${token}`).then((r) => r.data),
    enabled: !!token,
    // Poll every 5s so the page updates when the webhook fires after payment
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ['paid', 'partially_paid'].includes(status) ? false : 5_000
    },
  })
}

export function useCreateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => apiClient.post('/invoices', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useUpdateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => apiClient.put(`/invoices/${id}`, data).then((r) => r.data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['invoices', id] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

export function useDeleteInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => apiClient.delete(`/invoices/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useSendInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => apiClient.post(`/invoices/${id}/send`).then((r) => r.data),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['invoices', id] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

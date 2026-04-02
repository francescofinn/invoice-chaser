import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApiClient } from './client'

const OPERATOR_QUERY_KEY = ['operator', 'cases']

function replaceCaseInQueue(currentCases, nextCase) {
  if (!currentCases?.length) {
    return [nextCase]
  }

  const didReplace = currentCases.some((item) => item.invoice.id === nextCase.invoice.id)
  if (didReplace) {
    return currentCases.map((item) => (item.invoice.id === nextCase.invoice.id ? nextCase : item))
  }

  return [nextCase, ...currentCases]
}

function syncOperatorCase(queryClient, nextCase) {
  queryClient.setQueryData(OPERATOR_QUERY_KEY, (currentCases) => replaceCaseInQueue(currentCases, nextCase))
}

function refreshOperatorViews(queryClient) {
  queryClient.invalidateQueries({ queryKey: OPERATOR_QUERY_KEY })
  queryClient.invalidateQueries({ queryKey: ['dashboard'] })
}

export function useOperatorCases() {
  const api = useApiClient()
  return useQuery({
    queryKey: OPERATOR_QUERY_KEY,
    queryFn: () => api.get('/operator/cases').then((response) => response.data),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export function useAnalyzeOperatorCase() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (invoiceId) => api.post(`/operator/cases/${invoiceId}/analyze`).then((response) => response.data),
    onSuccess: (data) => {
      syncOperatorCase(queryClient, data)
      refreshOperatorViews(queryClient)
    },
  })
}

export function useSendOperatorDraft() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ invoiceId, draftSubject, draftBody }) =>
      api
        .post(`/operator/cases/${invoiceId}/send`, {
          draft_subject: draftSubject,
          draft_body: draftBody,
        })
        .then((response) => response.data),
    onSuccess: (data) => {
      syncOperatorCase(queryClient, data)
      refreshOperatorViews(queryClient)
    },
  })
}

export function useSimulateOperatorReply() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ invoiceId, replyText }) =>
      api
        .post(`/operator/cases/${invoiceId}/simulate-reply`, { reply_text: replyText })
        .then((response) => response.data),
    onSuccess: (data) => {
      syncOperatorCase(queryClient, data)
      refreshOperatorViews(queryClient)
    },
  })
}

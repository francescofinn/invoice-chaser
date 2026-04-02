import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useAnalyzeOperatorCase,
  useOperatorCases,
  useSendOperatorDraft,
  useSimulateOperatorReply,
} from '../../api/operator'

const formatCurrency = (value) =>
  '$' + Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const formatDate = (value) => {
  if (!value) return 'Not set'
  return new Date(`${value}T00:00:00`).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const formatDateTime = (value) => {
  if (!value) return 'Never'
  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

const formatLabel = (value) =>
  String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')

function getRiskStyles(riskLevel) {
  switch (riskLevel) {
    case 'high':
      return 'bg-red-50 text-red-700 border border-red-200'
    case 'medium':
      return 'bg-amber-50 text-amber-700 border border-amber-200'
    default:
      return 'bg-slate-100 text-slate-600 border border-slate-200'
  }
}

function getStatusStyles(status) {
  switch (status) {
    case 'payment_plan':
      return 'bg-indigo-50 text-indigo-700 border border-indigo-200'
    case 'promise_to_pay':
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
    case 'needs_human_review':
      return 'bg-amber-50 text-amber-700 border border-amber-200'
    case 'resolved':
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
    case 'awaiting_client':
      return 'bg-blue-50 text-blue-700 border border-blue-200'
    default:
      return 'bg-slate-100 text-slate-700 border border-slate-200'
  }
}

function buildCannedReplies() {
  const promiseDate = new Date()
  promiseDate.setDate(promiseDate.getDate() + 6)
  const promiseDateText = promiseDate.toISOString().slice(0, 10)

  return [
    {
      label: 'Half now, rest Friday',
      text: 'Can I pay half now and the rest Friday?',
      emphasis: true,
    },
    {
      label: `Promise full payment on ${promiseDateText}`,
      text: `I can pay the full amount on ${promiseDateText}.`,
      emphasis: false,
    },
    {
      label: 'Already paid elsewhere',
      text: 'I already paid this yesterday.',
      emphasis: false,
    },
  ]
}

function ForecastEntryList({ entries, tone }) {
  if (!entries?.length) {
    return <p className="text-sm text-slate-500">No forecast impact yet.</p>
  }

  const toneClass =
    tone === 'after'
      ? 'border-emerald-100 bg-emerald-50/70'
      : 'border-slate-200 bg-slate-50/80'

  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <div
          key={`${tone}-${entry.date}-${entry.invoice_ids.join('-')}`}
          className={`rounded-lg border px-3 py-2 ${toneClass}`}
        >
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{formatDate(entry.date)}</div>
          <div className="mt-1 text-base font-semibold text-slate-900">
            {formatCurrency(entry.expected_amount)}
          </div>
        </div>
      ))}
    </div>
  )
}

function ActiveCommitments({ commitments }) {
  const activeCommitments = commitments.filter((commitment) => commitment.status === 'active')

  if (!activeCommitments.length) {
    return <p className="text-sm text-slate-500">No active commitments yet.</p>
  }

  return (
    <div className="space-y-3">
      {activeCommitments.map((commitment) => (
        <div key={commitment.id} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">{formatLabel(commitment.commitment_type)}</p>
              <p className="mt-1 text-xs text-slate-500">Due {formatDate(commitment.due_date)}</p>
            </div>
            <span className="text-sm font-semibold text-slate-900">{formatCurrency(commitment.amount)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function ActivityTimeline({ activity }) {
  if (!activity.length) {
    return <p className="text-sm text-slate-500">No operator activity yet.</p>
  }

  return (
    <div className="space-y-3">
      {activity.map((item) => (
        <div key={item.id} className="relative rounded-xl border border-slate-200 bg-white px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">{item.title}</p>
              <p className="mt-1 text-xs uppercase tracking-wide text-slate-400">
                {formatLabel(item.activity_type)}
              </p>
            </div>
            <span className="text-xs text-slate-400">{formatDateTime(item.created_at)}</span>
          </div>
          {item.body ? <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{item.body}</p> : null}
        </div>
      ))}
    </div>
  )
}

export default function OperatorPanel() {
  const { data: operatorCases = [], isLoading, error } = useOperatorCases()
  const analyzeCase = useAnalyzeOperatorCase()
  const sendDraft = useSendOperatorDraft()
  const simulateReply = useSimulateOperatorReply()

  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null)
  const [draftSubject, setDraftSubject] = useState('')
  const [draftBody, setDraftBody] = useState('')
  const [manualReply, setManualReply] = useState('')
  const [forecastDelta, setForecastDelta] = useState(null)

  useEffect(() => {
    if (!operatorCases.length) {
      setSelectedInvoiceId(null)
      return
    }

    const hasSelectedCase = operatorCases.some((item) => item.invoice.id === selectedInvoiceId)
    if (!hasSelectedCase) {
      setSelectedInvoiceId(operatorCases[0].invoice.id)
    }
  }, [operatorCases, selectedInvoiceId])

  const selectedCase =
    operatorCases.find((item) => item.invoice.id === selectedInvoiceId) || operatorCases[0] || null

  useEffect(() => {
    setDraftSubject(selectedCase?.case.draft_subject || '')
    setDraftBody(selectedCase?.case.draft_body || '')
    setManualReply('')
    setForecastDelta(null)
  }, [selectedCase?.invoice.id, selectedCase?.case.draft_subject, selectedCase?.case.draft_body])

  const cannedReplies = buildCannedReplies()

  const handleAnalyze = () => {
    if (!selectedCase) return

    analyzeCase.mutate(selectedCase.invoice.id, {
      onSuccess: (data) => {
        setSelectedInvoiceId(data.invoice.id)
        setDraftSubject(data.case.draft_subject || '')
        setDraftBody(data.case.draft_body || '')
      },
    })
  }

  const handleSend = () => {
    if (!selectedCase) return

    sendDraft.mutate(
      {
        invoiceId: selectedCase.invoice.id,
        draftSubject,
        draftBody,
      },
      {
        onSuccess: (data) => {
          setSelectedInvoiceId(data.invoice.id)
          setDraftSubject(data.case.draft_subject || '')
          setDraftBody(data.case.draft_body || '')
        },
      },
    )
  }

  const submitReply = (replyText) => {
    if (!selectedCase || !replyText.trim()) return

    simulateReply.mutate(
      {
        invoiceId: selectedCase.invoice.id,
        replyText: replyText.trim(),
      },
      {
        onSuccess: (data) => {
          setSelectedInvoiceId(data.invoice.id)
          setDraftSubject(data.case.draft_subject || '')
          setDraftBody(data.case.draft_body || '')
          setManualReply('')
          setForecastDelta({
            before: data.forecast_before || [],
            after: data.forecast_after || [],
          })
        },
      },
    )
  }

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
          Loading operator queue...
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-base font-semibold text-red-900">Collections operator unavailable</h3>
        <p className="mt-2 text-sm text-red-700">
          The dashboard summary loaded, but the operator panel could not reach the new collections endpoints.
        </p>
      </section>
    )
  }

  if (!operatorCases.length || !selectedCase) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">AI Collections</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-900">Operator queue is clear</h3>
          </div>
          <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            No active cases
          </div>
        </div>
        <p className="mt-4 max-w-2xl text-sm text-slate-600">
          Outstanding invoices will appear here once they are sent, viewed, partially paid, or overdue.
        </p>
      </section>
    )
  }

  const replyActionsDisabled = !selectedCase.case.last_contacted_at || simulateReply.isPending

  return (
    <section className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-[linear-gradient(135deg,#f8fafc_0%,#eef2ff_55%,#fef3c7_100%)] px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">AI Collections</p>
            <h3 className="mt-2 text-2xl font-semibold text-slate-950">Operator Workbench</h3>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Analyze risk, send the next best outreach, and simulate inbound replies without leaving the dashboard.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full border border-slate-200 bg-white/80 px-4 py-2 text-sm text-slate-700">
              {operatorCases.length} queued account{operatorCases.length === 1 ? '' : 's'}
            </div>
            <div className="rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
              Demo controls live
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-slate-50/70 lg:border-b-0 lg:border-r">
          <div className="px-5 py-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-slate-900">Prioritized Queue</h4>
              <span className="text-xs text-slate-500">Server-ranked</span>
            </div>
            <div className="mt-4 space-y-3">
              {operatorCases.map((item) => {
                const isSelected = item.invoice.id === selectedCase.invoice.id
                return (
                  <button
                    key={item.invoice.id}
                    type="button"
                    onClick={() => setSelectedInvoiceId(item.invoice.id)}
                    className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                      isSelected
                        ? 'border-indigo-300 bg-white shadow-sm ring-2 ring-indigo-100'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{item.client.name}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.invoice.invoice_number}</p>
                      </div>
                      <span className="text-sm font-semibold text-slate-900">
                        {formatCurrency(item.remaining_amount)}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${getRiskStyles(item.case.risk_level)}`}>
                        {item.case.risk_level ? `${formatLabel(item.case.risk_level)} risk` : 'Needs analysis'}
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${getStatusStyles(item.case.status)}`}>
                        {formatLabel(item.case.status)}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                      <span>Due {formatDate(item.invoice.due_date)}</span>
                      <span>{item.invoice.status === 'overdue' ? 'Overdue' : formatLabel(item.invoice.status)}</span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </aside>

        <div className="p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="text-2xl font-semibold text-slate-950">{selectedCase.client.name}</h4>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusStyles(selectedCase.case.status)}`}>
                  {formatLabel(selectedCase.case.status)}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {selectedCase.client.company || selectedCase.client.email} · Invoice {selectedCase.invoice.invoice_number} ·
                {` `}Due {formatDate(selectedCase.invoice.due_date)}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Last contacted {formatDateTime(selectedCase.case.last_contacted_at)} · Queued follow-up{' '}
                {selectedCase.case.queued_follow_up_date ? formatDate(selectedCase.case.queued_follow_up_date) : 'Not scheduled'}
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to={`/invoices/${selectedCase.invoice.id}`}
                className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
              >
                Open invoice
              </Link>
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={analyzeCase.isPending}
                className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {analyzeCase.isPending ? 'Analyzing...' : 'Analyze account'}
              </button>
              <button
                type="button"
                onClick={handleSend}
                disabled={sendDraft.isPending || !draftSubject.trim() || !draftBody.trim()}
                className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {sendDraft.isPending ? 'Sending...' : 'Send draft'}
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Risk Summary</p>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${getRiskStyles(selectedCase.case.risk_level)}`}>
                  {selectedCase.case.risk_level ? formatLabel(selectedCase.case.risk_level) : 'Pending'}
                </span>
              </div>
              <p className="mt-4 text-sm leading-7 text-slate-700">
                {selectedCase.case.risk_summary ||
                  'Run analysis to generate a plain-English view of payment risk and the likely blocker.'}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-5">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Next Best Action</p>
              <h5 className="mt-4 text-lg font-semibold text-slate-900">
                {selectedCase.case.next_action_label || 'Waiting for operator analysis'}
              </h5>
              <p className="mt-2 text-sm leading-7 text-slate-700">
                {selectedCase.case.next_action_reason ||
                  'The recommended next step will appear here once the account has been analyzed.'}
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 2xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.9fr)]">
            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 p-5">
                <div className="flex items-center justify-between">
                  <h5 className="text-lg font-semibold text-slate-900">Draft Composer</h5>
                  <span className="text-sm text-slate-500">{formatCurrency(selectedCase.remaining_amount)} outstanding</span>
                </div>
                <div className="mt-4 space-y-4">
                  <label className="block">
                    <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Subject
                    </span>
                    <input
                      type="text"
                      value={draftSubject}
                      onChange={(event) => setDraftSubject(event.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
                      placeholder="Analyze the account to generate a draft"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Message
                    </span>
                    <textarea
                      value={draftBody}
                      onChange={(event) => setDraftBody(event.target.value)}
                      rows={8}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
                      placeholder="The editable draft body will appear here."
                    />
                  </label>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h5 className="text-lg font-semibold text-slate-900">Simulate Client Reply</h5>
                    <p className="mt-1 text-sm text-slate-500">Visible demo controls stay live in v1.</p>
                  </div>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
                    Simulated inbound only
                  </span>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  {cannedReplies.map((reply) => (
                    <button
                      key={reply.label}
                      type="button"
                      onClick={() => submitReply(reply.text)}
                      disabled={replyActionsDisabled}
                      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                        reply.emphasis
                          ? 'bg-amber-100 text-amber-900 hover:bg-amber-200'
                          : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      } disabled:cursor-not-allowed disabled:opacity-50`}
                    >
                      {reply.label}
                    </button>
                  ))}
                </div>

                <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <label className="block">
                    <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Custom reply
                    </span>
                    <textarea
                      value={manualReply}
                      onChange={(event) => setManualReply(event.target.value)}
                      rows={4}
                      className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
                      placeholder="Type a reply to test classification and forecast changes..."
                    />
                  </label>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs text-slate-500">
                      {selectedCase.case.last_contacted_at
                        ? 'Reply simulation is unlocked because the account has already been contacted.'
                        : 'Send a draft first to mirror the real demo flow.'}
                    </p>
                    <button
                      type="button"
                      onClick={() => submitReply(manualReply)}
                      disabled={replyActionsDisabled || !manualReply.trim()}
                      className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {simulateReply.isPending ? 'Classifying reply...' : 'Simulate client reply'}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 p-5">
                <div className="flex items-center justify-between">
                  <h5 className="text-lg font-semibold text-slate-900">Commitments</h5>
                  <span className="text-sm text-slate-500">
                    {selectedCase.case.last_reply_classification
                      ? formatLabel(selectedCase.case.last_reply_classification)
                      : 'No reply classified'}
                  </span>
                </div>
                <div className="mt-4">
                  <ActiveCommitments commitments={selectedCase.commitments} />
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-5">
                <h5 className="text-lg font-semibold text-slate-900">Forecast Delta</h5>
                <p className="mt-1 text-sm text-slate-500">
                  After a simulated reply, this shows how the selected account changed the forecast.
                </p>
                <div className="mt-4 grid gap-4 xl:grid-cols-2">
                  <div>
                    <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Before</p>
                    <ForecastEntryList entries={forecastDelta?.before || []} tone="before" />
                  </div>
                  <div>
                    <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">After</p>
                    <ForecastEntryList entries={forecastDelta?.after || []} tone="after" />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-5">
                <h5 className="text-lg font-semibold text-slate-900">Recent Activity</h5>
                <div className="mt-4">
                  <ActivityTimeline activity={selectedCase.recent_activity} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

import { useParams, useNavigate } from 'react-router-dom'
import { useInvoice, useSendInvoice, useDeleteInvoice } from '../api/invoices'

const STATUS_STYLES = {
  draft: 'bg-gray-100 text-gray-600',
  sent: 'bg-blue-100 text-blue-700',
  viewed: 'bg-purple-100 text-purple-700',
  partially_paid: 'bg-yellow-100 text-yellow-700',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
}

export default function InvoiceDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: invoice, isLoading, error } = useInvoice(id)
  const sendInvoice = useSendInvoice()
  const deleteInvoice = useDeleteInvoice()

  if (isLoading) {
    return (
      <div className="p-8 flex items-center gap-2 text-gray-400 text-sm">
        <span className="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full" />
        Loading...
      </div>
    )
  }

  if (error || !invoice) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          Invoice not found.
        </div>
      </div>
    )
  }

  const total = invoice.line_items.reduce(
    (sum, item) => sum + Number(item.quantity) * Number(item.unit_price),
    0
  )

  const handleSend = () => {
    sendInvoice.mutate(Number(id))
  }

  const handleDelete = () => {
    if (!confirm('Delete this invoice? This cannot be undone.')) return
    deleteInvoice.mutate(Number(id), {
      onSuccess: () => navigate('/invoices'),
    })
  }

  const paymentUrl = `${window.location.origin}/pay/${invoice.token}`

  return (
    <div className="p-8 max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">{invoice.invoice_number}</h2>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                STATUS_STYLES[invoice.status] || 'bg-gray-100 text-gray-600'
              }`}
            >
              {invoice.status.replace('_', ' ')}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {invoice.client?.name}
            {invoice.client?.company ? ` · ${invoice.client.company}` : ''}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            Issued {new Date(invoice.issue_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            {' · '}
            Due {new Date(invoice.due_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {invoice.status === 'draft' && (
            <>
              <button
                onClick={handleSend}
                disabled={sendInvoice.isPending}
                className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {sendInvoice.isPending ? 'Sending...' : 'Send Invoice'}
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteInvoice.isPending}
                className="text-gray-400 hover:text-red-500 px-3 py-2 rounded-md text-sm transition-colors"
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {sendInvoice.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          Invoice sent! The client has been emailed a payment link.
        </div>
      )}
      {sendInvoice.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          Failed to send invoice. Please try again.
        </div>
      )}

      {/* Line items */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr className="text-left text-gray-500">
              <th className="px-5 py-3 font-medium">Description</th>
              <th className="px-5 py-3 font-medium text-right w-20">Qty</th>
              <th className="px-5 py-3 font-medium text-right w-28">Unit Price</th>
              <th className="px-5 py-3 font-medium text-right w-24">Subtotal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {invoice.line_items.map((item, i) => (
              <tr key={i}>
                <td className="px-5 py-3 text-gray-700">{item.description}</td>
                <td className="px-5 py-3 text-right text-gray-700">{item.quantity}</td>
                <td className="px-5 py-3 text-right text-gray-700">
                  ${Number(item.unit_price).toFixed(2)}
                </td>
                <td className="px-5 py-3 text-right font-medium text-gray-900">
                  ${(Number(item.quantity) * Number(item.unit_price)).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex justify-end px-5 py-4 border-t border-gray-200 bg-gray-50">
          <div className="text-right">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Total</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">
              ${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>
      </div>

      {/* Notes */}
      {invoice.notes && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Notes</p>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{invoice.notes}</p>
        </div>
      )}

      {/* Payment link (once sent) */}
      {invoice.status !== 'draft' && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Client Payment Link
          </p>
          <div className="flex items-center gap-2">
            <input
              readOnly
              value={paymentUrl}
              className="flex-1 border border-gray-200 rounded px-3 py-1.5 text-sm text-gray-600 bg-gray-50 font-mono"
            />
            <button
              onClick={() => navigator.clipboard.writeText(paymentUrl)}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium px-2 py-1.5 border border-indigo-200 rounded hover:bg-indigo-50 transition-colors"
            >
              Copy
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

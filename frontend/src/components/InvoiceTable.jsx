import { Link } from 'react-router-dom'

const STATUS_STYLES = {
  draft: 'bg-gray-100 text-gray-600',
  sent: 'bg-blue-100 text-blue-700',
  viewed: 'bg-purple-100 text-purple-700',
  partially_paid: 'bg-yellow-100 text-yellow-700',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
}

function isAtRisk(invoice) {
  if (!['sent', 'viewed'].includes(invoice.status)) return false
  const due = new Date(invoice.due_date + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const daysUntilDue = Math.ceil((due - today) / 86_400_000)
  return daysUntilDue >= 0 && daysUntilDue <= 7
}

export default function InvoiceTable({ invoices }) {
  if (!invoices || invoices.length === 0) {
    return <p className="text-sm text-gray-400 py-4 text-center">No invoices found.</p>
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-gray-500 border-b border-gray-200">
          <th className="pb-3 font-medium">Invoice</th>
          <th className="pb-3 font-medium">Client</th>
          <th className="pb-3 font-medium">Amount</th>
          <th className="pb-3 font-medium">Due Date</th>
          <th className="pb-3 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {invoices.map((inv) => (
          <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
            <td className="py-3 pr-4">
              <Link
                to={`/invoices/${inv.id}`}
                className="font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
              >
                {inv.invoice_number}
              </Link>
            </td>
            <td className="py-3 pr-4 text-gray-700">
              <div>{inv.client?.name}</div>
              {inv.client?.company && (
                <div className="text-xs text-gray-400">{inv.client.company}</div>
              )}
            </td>
            <td className="py-3 pr-4 font-medium text-gray-900">
              ${Number(inv.total).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </td>
            <td className="py-3 pr-4 text-gray-500">
              {new Date(inv.due_date + 'T00:00:00').toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </td>
            <td className="py-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    STATUS_STYLES[inv.status] || 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {inv.status.replace('_', ' ')}
                </span>
                {isAtRisk(inv) && (
                  <span className="text-xs text-amber-600 font-medium" title="Due within 7 days">
                    ⚠ At Risk
                  </span>
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const fmt = (n) =>
  '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export default function SummaryCards({ summary }) {
  const activeCount = Object.entries(summary.invoice_count_by_status)
    .filter(([s]) => s !== 'draft' && s !== 'paid')
    .reduce((a, [, v]) => a + v, 0)

  const cards = [
    {
      label: 'Total Outstanding',
      value: fmt(summary.total_outstanding),
      sub: 'unpaid invoices',
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Total Overdue',
      value: fmt(summary.total_overdue),
      sub: 'past due date',
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
    {
      label: 'Collected This Month',
      value: fmt(summary.total_paid_this_month),
      sub: 'payments received',
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Active Invoices',
      value: activeCount,
      sub: 'sent or overdue',
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map(({ label, value, sub, color, bg }) => (
        <div key={label} className="bg-white rounded-lg border border-gray-200 p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
          <p className={`text-2xl font-bold ${color} mt-2`}>{value}</p>
          <p className="text-xs text-gray-400 mt-1">{sub}</p>
        </div>
      ))}
    </div>
  )
}

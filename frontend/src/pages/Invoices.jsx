import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useInvoices } from '../api/invoices'
import InvoiceTable from '../components/InvoiceTable'

const STATUS_TABS = [
  { label: 'All', value: undefined },
  { label: 'Draft', value: 'draft' },
  { label: 'Sent', value: 'sent' },
  { label: 'Viewed', value: 'viewed' },
  { label: 'Overdue', value: 'overdue' },
  { label: 'Paid', value: 'paid' },
]

function isAtRisk(invoice) {
  if (!['sent', 'viewed'].includes(invoice.status)) return false
  const due = new Date(invoice.due_date + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.ceil((due - today) / 86_400_000) <= 7
}

export default function Invoices() {
  const [statusFilter, setStatusFilter] = useState(undefined)
  const [search, setSearch] = useState('')
  const [atRiskOnly, setAtRiskOnly] = useState(false)
  const [sortBy, setSortBy] = useState('due_date') // due_date | amount | status

  const { data: invoices = [], isLoading } = useInvoices(statusFilter)

  const filtered = useMemo(() => {
    let list = [...invoices]

    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(
        (inv) =>
          inv.invoice_number.toLowerCase().includes(q) ||
          inv.client?.name?.toLowerCase().includes(q) ||
          inv.client?.company?.toLowerCase().includes(q)
      )
    }

    if (atRiskOnly) {
      list = list.filter(isAtRisk)
    }

    if (sortBy === 'amount') {
      list.sort((a, b) => Number(b.total) - Number(a.total))
    } else if (sortBy === 'status') {
      const order = ['overdue', 'viewed', 'sent', 'partially_paid', 'draft', 'paid']
      list.sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status))
    }
    // due_date is already sorted by backend

    return list
  }, [invoices, search, atRiskOnly, sortBy])

  const atRiskCount = useMemo(() => invoices.filter(isAtRisk).length, [invoices])

  return (
    <div className="p-8 space-y-5">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Invoices</h2>
        <Link
          to="/invoices/new"
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          New Invoice
        </Link>
      </div>

      {/* Status tabs */}
      <div className="flex gap-0 border-b border-gray-200">
        {STATUS_TABS.map((f) => (
          <button
            key={f.label}
            onClick={() => setStatusFilter(f.value)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              statusFilter === f.value
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search invoice # or client..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 bg-white"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Sort */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-300 bg-white"
        >
          <option value="due_date">Sort: Due Date</option>
          <option value="amount">Sort: Amount</option>
          <option value="status">Sort: Status</option>
        </select>

        {/* At-risk toggle */}
        <button
          onClick={() => setAtRiskOnly((v) => !v)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
            atRiskOnly
              ? 'bg-amber-50 border-amber-300 text-amber-700'
              : 'bg-white border-gray-200 text-gray-500 hover:border-amber-300 hover:text-amber-600'
          }`}
        >
          <span>⚠</span>
          At Risk
          {atRiskCount > 0 && (
            <span className={`text-xs rounded-full px-1.5 py-0.5 font-semibold ${atRiskOnly ? 'bg-amber-200 text-amber-800' : 'bg-gray-100 text-gray-500'}`}>
              {atRiskCount}
            </span>
          )}
        </button>

        {/* Result count */}
        {(search || atRiskOnly) && (
          <span className="text-sm text-gray-400 ml-1">
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full" />
            Loading...
          </div>
        ) : (
          <InvoiceTable invoices={filtered} />
        )}
      </div>
    </div>
  )
}

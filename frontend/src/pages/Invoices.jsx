import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useInvoices } from '../api/invoices'
import InvoiceTable from '../components/InvoiceTable'

const FILTERS = [
  { label: 'All', value: undefined },
  { label: 'Draft', value: 'draft' },
  { label: 'Sent', value: 'sent' },
  { label: 'Overdue', value: 'overdue' },
  { label: 'Paid', value: 'paid' },
]

export default function Invoices() {
  const [filter, setFilter] = useState(undefined)
  const { data: invoices = [], isLoading } = useInvoices(filter)

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

      {/* Filter tabs */}
      <div className="flex gap-0 border-b border-gray-200">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              filter === f.value
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full" />
            Loading...
          </div>
        ) : (
          <InvoiceTable invoices={invoices} />
        )}
      </div>
    </div>
  )
}

import { Link } from 'react-router-dom'
import { useDashboardSummary } from '../api/dashboard'
import { useInvoices } from '../api/invoices'
import SummaryCards from '../components/SummaryCards'
import CashFlowChart from '../components/CashFlowChart'
import InvoiceTable from '../components/InvoiceTable'

export default function Dashboard() {
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useDashboardSummary()
  const { data: invoices = [] } = useInvoices()

  if (summaryLoading) {
    return (
      <div className="p-8 flex items-center gap-2 text-gray-400 text-sm">
        <span className="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full" />
        Loading...
      </div>
    )
  }

  if (summaryError) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          Failed to load dashboard. Make sure the backend is running at{' '}
          {import.meta.env.VITE_API_URL || 'http://localhost:8000'}.
        </div>
      </div>
    )
  }

  const recentInvoices = invoices
    .slice()
    .sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date))
    .slice(0, 10)

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <Link
          to="/invoices/new"
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          New Invoice
        </Link>
      </div>

      <SummaryCards summary={summary} />

      <CashFlowChart data={summary.cash_flow_forecast} />

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-medium text-gray-700">Recent Invoices</h3>
          <Link to="/invoices" className="text-xs text-indigo-600 hover:underline">
            View all
          </Link>
        </div>
        <InvoiceTable invoices={recentInvoices} />
      </div>
    </div>
  )
}

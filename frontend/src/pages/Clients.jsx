import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useClients } from '../api/clients'
import { useClientProfile } from '../api/clients'

const STATUS_STYLES = {
  draft: 'bg-gray-100 text-gray-600',
  sent: 'bg-blue-100 text-blue-700',
  viewed: 'bg-purple-100 text-purple-700',
  partially_paid: 'bg-yellow-100 text-yellow-700',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
}

function ClientProfile({ clientId, onClose }) {
  const { data, isLoading } = useClientProfile(clientId)

  const stats = useMemo(() => {
    if (!data?.invoices) return null
    const total = data.invoices.reduce((s, inv) => s + Number(inv.total), 0)
    const paid = data.invoices.filter((i) => i.status === 'paid').reduce((s, inv) => s + Number(inv.total), 0)
    const overdue = data.invoices.filter((i) => i.status === 'overdue').length
    return { total, paid, overdue, count: data.invoices.length }
  }, [data])

  return (
    <div className="fixed inset-0 z-40 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" />
      <aside
        className="relative z-50 w-[480px] bg-white h-full shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <span className="text-sm font-semibold text-gray-700">Client Profile</span>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-100">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <span className="animate-spin w-5 h-5 border-2 border-gray-200 border-t-indigo-500 rounded-full" />
          </div>
        ) : data ? (
          <div className="flex-1 overflow-y-auto">
            {/* Identity */}
            <div className="px-6 py-6 border-b border-gray-100">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-lg shrink-0">
                  {data.name[0].toUpperCase()}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{data.name}</h2>
                  {data.company && <p className="text-sm text-gray-500">{data.company}</p>}
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <a href={`mailto:${data.email}`} className="hover:text-indigo-600">{data.email}</a>
              </div>
            </div>

            {/* Stats */}
            {stats && (
              <div className="grid grid-cols-3 divide-x divide-gray-100 border-b border-gray-100">
                <div className="px-5 py-4 text-center">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Invoices</p>
                  <p className="text-xl font-bold text-gray-900">{stats.count}</p>
                </div>
                <div className="px-5 py-4 text-center">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Billed</p>
                  <p className="text-xl font-bold text-gray-900">
                    ${stats.total.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </p>
                </div>
                <div className="px-5 py-4 text-center">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Overdue</p>
                  <p className={`text-xl font-bold ${stats.overdue > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                    {stats.overdue}
                  </p>
                </div>
              </div>
            )}

            {/* Invoices list */}
            <div className="px-6 py-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Invoice History</h3>
              {data.invoices.length === 0 ? (
                <p className="text-sm text-gray-400">No invoices yet.</p>
              ) : (
                <div className="space-y-2">
                  {[...data.invoices]
                    .sort((a, b) => new Date(b.due_date) - new Date(a.due_date))
                    .map((inv) => (
                    <Link
                      key={inv.id}
                      to={`/invoices/${inv.id}`}
                      onClick={onClose}
                      className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-colors group"
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-800 group-hover:text-indigo-700">
                          {inv.invoice_number}
                        </p>
                        <p className="text-xs text-gray-400">
                          Due {new Date(inv.due_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-semibold text-gray-700">
                          ${Number(inv.total).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[inv.status] || 'bg-gray-100 text-gray-600'}`}>
                          {inv.status.replace('_', ' ')}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </aside>
    </div>
  )
}

export default function Clients() {
  const { data: clients = [], isLoading } = useClients()
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return clients
    return clients.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        (c.company || '').toLowerCase().includes(q)
    )
  }, [clients, search])

  return (
    <div className="p-8 space-y-5">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Clients</h2>
        <span className="text-sm text-gray-400">{clients.length} total</span>
      </div>

      {/* Search */}
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          type="text"
          placeholder="Search by name, email or company..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 bg-white"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm p-6">
            <span className="animate-spin w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full" />
            Loading...
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-gray-400 p-6 text-center">
            {search ? `No clients matching "${search}"` : 'No clients yet.'}
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200 bg-gray-50">
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Company</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Since</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedId(c.id)}
                >
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-semibold text-xs shrink-0">
                        {c.name[0].toUpperCase()}
                      </div>
                      <span className="font-medium text-gray-800">{c.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-gray-500">{c.company || '—'}</td>
                  <td className="px-5 py-3.5 text-gray-500">{c.email}</td>
                  <td className="px-5 py-3.5 text-gray-400">
                    {new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <span className="text-xs text-indigo-500 font-medium group-hover:underline">View →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selectedId && (
        <ClientProfile clientId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  )
}

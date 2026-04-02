import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useClients, useCreateClient } from '../api/clients'
import { useCreateInvoice } from '../api/invoices'
import LineItemEditor from '../components/LineItemEditor'

const today = () => new Date().toISOString().split('T')[0]
const in30 = () => new Date(Date.now() + 30 * 86_400_000).toISOString().split('T')[0]
const nextInvoiceNumber = () => `INV-${Date.now().toString().slice(-6)}`

export default function NewInvoice() {
  const navigate = useNavigate()
  const { data: clients = [], isLoading: clientsLoading } = useClients()
  const createInvoice = useCreateInvoice()
  const createClient = useCreateClient()

  const [form, setForm] = useState({
    client_id: '',
    invoice_number: nextInvoiceNumber(),
    issue_date: today(),
    due_date: in30(),
    notes: '',
  })
  const [lineItems, setLineItems] = useState([{ description: '', quantity: 1, unit_price: 0 }])

  // Inline new client form state
  const [showNewClient, setShowNewClient] = useState(false)
  const [newClient, setNewClient] = useState({ name: '', email: '', company: '' })

  const handleAddClient = async (e) => {
    e.preventDefault()
    createClient.mutate(newClient, {
      onSuccess: (created) => {
        setForm((f) => ({ ...f, client_id: String(created.id) }))
        setNewClient({ name: '', email: '', company: '' })
        setShowNewClient(false)
      },
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.client_id) return
    createInvoice.mutate(
      {
        ...form,
        client_id: Number(form.client_id),
        line_items: lineItems.map((item) => ({
          description: item.description,
          quantity: Number(item.quantity),
          unit_price: Number(item.unit_price),
        })),
      },
      {
        onSuccess: (inv) => navigate(`/invoices/${inv.id}`),
      }
    )
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/invoices" className="text-gray-400 hover:text-gray-600 text-sm">
          ← Invoices
        </Link>
        <span className="text-gray-300">/</span>
        <h2 className="text-2xl font-bold text-gray-900">New Invoice</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Client selector */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
          <h3 className="text-sm font-medium text-gray-700">Client</h3>

          {!showNewClient ? (
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <select
                  required
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  value={form.client_id}
                  onChange={(e) => setForm({ ...form, client_id: e.target.value })}
                  disabled={clientsLoading}
                >
                  <option value="">Select a client...</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}{c.company ? ` — ${c.company}` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => setShowNewClient(true)}
                className="text-sm text-indigo-600 hover:text-indigo-800 font-medium whitespace-nowrap"
              >
                + New client
              </button>
            </div>
          ) : (
            <div className="border border-indigo-100 bg-indigo-50 rounded-md p-4 space-y-3">
              <p className="text-xs font-medium text-indigo-700 uppercase tracking-wide">New Client</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Name *</label>
                  <input
                    required
                    type="text"
                    className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    value={newClient.name}
                    onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Email *</label>
                  <input
                    required
                    type="email"
                    className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    value={newClient.email}
                    onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs text-gray-500 mb-1">Company</label>
                  <input
                    type="text"
                    className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    value={newClient.company}
                    onChange={(e) => setNewClient({ ...newClient, company: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleAddClient}
                  disabled={createClient.isPending}
                  className="bg-indigo-600 text-white px-3 py-1.5 rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
                >
                  {createClient.isPending ? 'Saving...' : 'Save Client'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowNewClient(false)}
                  className="text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded text-xs"
                >
                  Cancel
                </button>
              </div>
              {createClient.isError && (
                <p className="text-xs text-red-600">Failed to create client. Check email is unique.</p>
              )}
            </div>
          )}
        </div>

        {/* Invoice details */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
          <h3 className="text-sm font-medium text-gray-700">Invoice Details</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Invoice Number *</label>
              <input
                type="text"
                required
                className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                value={form.invoice_number}
                onChange={(e) => setForm({ ...form, invoice_number: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Issue Date *</label>
              <input
                type="date"
                required
                className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                value={form.issue_date}
                onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Due Date *</label>
              <input
                type="date"
                required
                className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                value={form.due_date}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              />
            </div>
          </div>
        </div>

        {/* Line items */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-3">
          <h3 className="text-sm font-medium text-gray-700">Line Items</h3>
          <LineItemEditor items={lineItems} onChange={setLineItems} />
        </div>

        {/* Notes */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Notes <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <textarea
            rows={3}
            className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400 resize-none"
            placeholder="Payment terms, bank details, thank you message..."
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </div>

        {createInvoice.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            Failed to create invoice. Check all required fields and try again.
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={createInvoice.isPending || !form.client_id}
            className="bg-indigo-600 text-white px-6 py-2.5 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {createInvoice.isPending ? 'Creating...' : 'Create Invoice'}
          </button>
          <Link
            to="/invoices"
            className="text-gray-500 hover:text-gray-700 px-6 py-2.5 rounded-md text-sm font-medium border border-gray-200 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  )
}

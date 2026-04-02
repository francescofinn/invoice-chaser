# Invoice Chaser — Frontend Implementation Plan

## Ownership
This doc covers everything in `frontend/`. The backend developer works in `backend/` in parallel. The **API Contract** section at the bottom describes the exact response shapes to expect — do not rely on the backend being ready to start building; use the contract to mock data.

---

## Stack
- React 18, Vite 5, Tailwind CSS 3, React Router v6
- TanStack Query v5 (React Query)
- Recharts (cash flow chart)
- Stripe.js + `@stripe/react-stripe-js` (payment portal)
- Axios (HTTP client)

---

## Project Structure to Create

```
frontend/
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html
└── src/
    ├── main.jsx               # ReactDOM root, QueryClientProvider, BrowserRouter
    ├── App.jsx                # Route definitions
    ├── api/
    │   ├── client.js          # Axios instance with baseURL from VITE_API_URL
    │   ├── invoices.js        # React Query hooks for invoices
    │   ├── clients.js         # React Query hooks for clients
    │   └── dashboard.js       # React Query hook for dashboard summary
    ├── pages/
    │   ├── Dashboard.jsx
    │   ├── Invoices.jsx
    │   ├── InvoiceDetail.jsx
    │   ├── NewInvoice.jsx
    │   └── PaymentPortal.jsx
    └── components/
        ├── Layout.jsx         # Sidebar nav wrapper for admin routes
        ├── InvoiceTable.jsx
        ├── SummaryCards.jsx
        ├── CashFlowChart.jsx
        └── LineItemEditor.jsx
```

---

## Environment Variables

Create `frontend/.env` (not committed):
```
VITE_API_URL=http://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

Both vars must be prefixed with `VITE_` to be accessible in the browser via `import.meta.env`.

---

## `package.json`

```json
{
  "name": "invoice-chaser-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@tanstack/react-query": "^5.40.0",
    "axios": "^1.7.0",
    "recharts": "^2.12.0",
    "@stripe/react-stripe-js": "^2.7.0",
    "@stripe/stripe-js": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "vite": "^5.2.0"
  }
}
```

---

## Config Files

### `vite.config.js`
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  }
})
```

### `tailwind.config.js`
```js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

### `postcss.config.js`
```js
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} }
}
```

### `index.html`
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Invoice Chaser</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

---

## `src/main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'  // Tailwind base styles

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
```

Add `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## `src/App.jsx`

```jsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import InvoiceDetail from './pages/InvoiceDetail'
import NewInvoice from './pages/NewInvoice'
import PaymentPortal from './pages/PaymentPortal'

export default function App() {
  return (
    <Routes>
      {/* Admin routes — wrapped in sidebar Layout */}
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/invoices" element={<Invoices />} />
        <Route path="/invoices/new" element={<NewInvoice />} />
        <Route path="/invoices/:id" element={<InvoiceDetail />} />
      </Route>

      {/* Public payment portal — no nav, no layout */}
      <Route path="/pay/:token" element={<PaymentPortal />} />
    </Routes>
  )
}
```

---

## `src/api/client.js`

```js
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export default apiClient
```

---

## `src/api/invoices.js`

```js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'

export function useInvoices(status) {
  return useQuery({
    queryKey: ['invoices', status],
    queryFn: () => apiClient.get('/invoices', { params: status ? { status } : {} }).then(r => r.data),
  })
}

export function useInvoice(id) {
  return useQuery({
    queryKey: ['invoices', id],
    queryFn: () => apiClient.get(`/invoices/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

export function usePublicInvoice(token) {
  return useQuery({
    queryKey: ['invoices', 'public', token],
    queryFn: () => apiClient.get(`/invoices/public/${token}`).then(r => r.data),
    enabled: !!token,
  })
}

export function useCreateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => apiClient.post('/invoices', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useUpdateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => apiClient.put(`/invoices/${id}`, data).then(r => r.data),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['invoices', id] }),
  })
}

export function useSendInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => apiClient.post(`/invoices/${id}/send`).then(r => r.data),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['invoices', id] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}
```

---

## `src/api/clients.js`

```js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'

export function useClients() {
  return useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.get('/clients').then(r => r.data),
  })
}

export function useCreateClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => apiClient.post('/clients', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clients'] }),
  })
}
```

---

## `src/api/dashboard.js`

```js
import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => apiClient.get('/dashboard/summary').then(r => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}
```

---

## `src/components/Layout.jsx`

Sidebar nav for admin routes. Uses React Router's `<Outlet />`.

```jsx
import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', exact: true },
  { to: '/invoices', label: 'Invoices' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-6 py-5 border-b border-gray-200">
          <h1 className="text-lg font-bold text-indigo-600">Invoice Chaser</h1>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
```

---

## `src/components/SummaryCards.jsx`

Receives `summary` object from `useDashboardSummary()`. Shows 4 stat cards.

```jsx
const fmt = (n) => `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2 })}`

const cards = (summary) => [
  { label: 'Total Outstanding', value: fmt(summary.total_outstanding), color: 'blue' },
  { label: 'Total Overdue', value: fmt(summary.total_overdue), color: 'red' },
  { label: 'Paid This Month', value: fmt(summary.total_paid_this_month), color: 'green' },
  { label: 'Active Invoices', value: Object.values(summary.invoice_count_by_status).reduce((a, b) => a + b, 0), color: 'purple' },
]

export default function SummaryCards({ summary }) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {cards(summary).map(({ label, value, color }) => (
        <div key={label} className="bg-white rounded-lg border border-gray-200 p-5">
          <p className="text-sm text-gray-500">{label}</p>
          <p className={`text-2xl font-bold text-${color}-600 mt-1`}>{value}</p>
        </div>
      ))}
    </div>
  )
}
```

---

## `src/components/CashFlowChart.jsx`

Receives `data` array from `summary.cash_flow_forecast`. Renders an Recharts AreaChart.

```jsx
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function CashFlowChart({ data }) {
  const formatted = data.map(d => ({
    ...d,
    label: new Date(d.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }))

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="text-sm font-medium text-gray-700 mb-4">Cash Flow Forecast (Next 90 Days)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={formatted} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
          <Tooltip formatter={v => [`$${Number(v).toLocaleString()}`, 'Expected']} />
          <Area type="monotone" dataKey="expected_amount" stroke="#6366f1" fill="#e0e7ff" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
```

---

## `src/components/InvoiceTable.jsx`

Receives `invoices` array. Shows number, client, amount, due date, status badge, and link to detail page. Highlights overdue rows.

**Late payment risk indicator**: flag invoices where `due_date` is within 7 days from today AND status is `sent` or `viewed` — show a yellow "At Risk" badge.

```jsx
import { Link } from 'react-router-dom'

const STATUS_STYLES = {
  draft:           'bg-gray-100 text-gray-600',
  sent:            'bg-blue-100 text-blue-700',
  viewed:          'bg-purple-100 text-purple-700',
  partially_paid:  'bg-yellow-100 text-yellow-700',
  paid:            'bg-green-100 text-green-700',
  overdue:         'bg-red-100 text-red-700',
}

function isAtRisk(invoice) {
  if (!['sent', 'viewed'].includes(invoice.status)) return false
  const due = new Date(invoice.due_date)
  const today = new Date()
  const daysUntilDue = Math.ceil((due - today) / 86400000)
  return daysUntilDue <= 7 && daysUntilDue >= 0
}

export default function InvoiceTable({ invoices }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-gray-500 border-b border-gray-200">
          <th className="pb-2 font-medium">Invoice</th>
          <th className="pb-2 font-medium">Client</th>
          <th className="pb-2 font-medium">Amount</th>
          <th className="pb-2 font-medium">Due Date</th>
          <th className="pb-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {invoices.map(inv => (
          <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50">
            <td className="py-3">
              <Link to={`/invoices/${inv.id}`} className="font-medium text-indigo-600 hover:underline">
                {inv.invoice_number}
              </Link>
            </td>
            <td className="py-3 text-gray-700">{inv.client?.name}</td>
            <td className="py-3 font-medium">${Number(inv.total).toLocaleString()}</td>
            <td className="py-3 text-gray-500">{new Date(inv.due_date + 'T00:00:00').toLocaleDateString()}</td>
            <td className="py-3">
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[inv.status] || ''}`}>
                {inv.status.replace('_', ' ')}
              </span>
              {isAtRisk(inv) && (
                <span className="ml-2 text-xs text-yellow-600 font-medium">⚠ At Risk</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

---

## `src/components/LineItemEditor.jsx`

Used in `NewInvoice.jsx`. Manages an array of `{description, quantity, unit_price}` with add/remove/edit controls.

```jsx
export default function LineItemEditor({ items, onChange }) {
  const add = () => onChange([...items, { description: '', quantity: 1, unit_price: 0 }])
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i))
  const update = (i, field, value) => {
    const next = [...items]
    next[i] = { ...next[i], [field]: value }
    onChange(next)
  }

  const total = items.reduce((sum, item) => sum + Number(item.quantity) * Number(item.unit_price), 0)

  return (
    <div>
      <table className="w-full text-sm mb-3">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-200">
            <th className="pb-2">Description</th>
            <th className="pb-2 w-20">Qty</th>
            <th className="pb-2 w-28">Unit Price</th>
            <th className="pb-2 w-24 text-right">Subtotal</th>
            <th className="pb-2 w-10" />
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-gray-100">
              <td className="py-1 pr-2">
                <input
                  className="w-full border border-gray-200 rounded px-2 py-1"
                  value={item.description}
                  onChange={e => update(i, 'description', e.target.value)}
                  placeholder="Service or product"
                />
              </td>
              <td className="py-1 pr-2">
                <input type="number" min="0" className="w-full border border-gray-200 rounded px-2 py-1"
                  value={item.quantity} onChange={e => update(i, 'quantity', e.target.value)} />
              </td>
              <td className="py-1 pr-2">
                <input type="number" min="0" step="0.01" className="w-full border border-gray-200 rounded px-2 py-1"
                  value={item.unit_price} onChange={e => update(i, 'unit_price', e.target.value)} />
              </td>
              <td className="py-1 text-right text-gray-700">
                ${(Number(item.quantity) * Number(item.unit_price)).toFixed(2)}
              </td>
              <td className="py-1 text-center">
                <button onClick={() => remove(i)} className="text-red-400 hover:text-red-600 text-lg leading-none">×</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex justify-between items-center">
        <button
          type="button"
          onClick={add}
          className="text-sm text-indigo-600 hover:underline"
        >
          + Add line item
        </button>
        <p className="font-semibold text-gray-800">Total: ${total.toFixed(2)}</p>
      </div>
    </div>
  )
}
```

---

## `src/pages/Dashboard.jsx`

```jsx
import { useDashboardSummary } from '../api/dashboard'
import { useInvoices } from '../api/invoices'
import SummaryCards from '../components/SummaryCards'
import CashFlowChart from '../components/CashFlowChart'
import InvoiceTable from '../components/InvoiceTable'

export default function Dashboard() {
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary()
  const { data: invoices } = useInvoices()

  if (summaryLoading) return <div className="p-8 text-gray-400">Loading...</div>

  return (
    <div className="p-8 space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
      <SummaryCards summary={summary} />
      <CashFlowChart data={summary.cash_flow_forecast} />
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-sm font-medium text-gray-700 mb-4">Recent Invoices</h3>
        <InvoiceTable invoices={(invoices || []).slice(0, 10)} />
      </div>
    </div>
  )
}
```

---

## `src/pages/Invoices.jsx`

Invoice list with status filter tabs (All / Sent / Overdue / Paid).

```jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useInvoices } from '../api/invoices'
import InvoiceTable from '../components/InvoiceTable'

const FILTERS = [
  { label: 'All', value: undefined },
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
        <Link to="/invoices/new" className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
          New Invoice
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {FILTERS.map(f => (
          <button
            key={f.label}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              filter === f.value
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        {isLoading ? (
          <p className="text-gray-400 text-sm">Loading...</p>
        ) : invoices.length === 0 ? (
          <p className="text-gray-400 text-sm">No invoices found.</p>
        ) : (
          <InvoiceTable invoices={invoices} />
        )}
      </div>
    </div>
  )
}
```

---

## `src/pages/NewInvoice.jsx`

Form to create a new invoice. Client selector (from `useClients()`), date pickers, `LineItemEditor`, notes, submit.

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClients } from '../api/clients'
import { useCreateInvoice } from '../api/invoices'
import LineItemEditor from '../components/LineItemEditor'

export default function NewInvoice() {
  const navigate = useNavigate()
  const { data: clients = [] } = useClients()
  const createInvoice = useCreateInvoice()

  const today = new Date().toISOString().split('T')[0]
  const in30 = new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0]

  const [form, setForm] = useState({
    client_id: '',
    invoice_number: `INV-${Date.now()}`,
    issue_date: today,
    due_date: in30,
    notes: '',
  })
  const [lineItems, setLineItems] = useState([{ description: '', quantity: 1, unit_price: 0 }])

  const handleSubmit = (e) => {
    e.preventDefault()
    createInvoice.mutate(
      { ...form, client_id: Number(form.client_id), line_items: lineItems },
      { onSuccess: (inv) => navigate(`/invoices/${inv.id}`) }
    )
  }

  return (
    <div className="p-8 max-w-3xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">New Invoice</h2>
      <form onSubmit={handleSubmit} className="space-y-5 bg-white border border-gray-200 rounded-lg p-6">
        {/* Client selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
          <select
            required
            className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm"
            value={form.client_id}
            onChange={e => setForm({ ...form, client_id: e.target.value })}
          >
            <option value="">Select client...</option>
            {clients.map(c => <option key={c.id} value={c.id}>{c.name} — {c.company}</option>)}
          </select>
        </div>

        {/* Invoice number, dates */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Invoice Number', key: 'invoice_number', type: 'text' },
            { label: 'Issue Date', key: 'issue_date', type: 'date' },
            { label: 'Due Date', key: 'due_date', type: 'date' },
          ].map(({ label, key, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type={type}
                required
                className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm"
                value={form[key]}
                onChange={e => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
        </div>

        {/* Line items */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Line Items</label>
          <LineItemEditor items={lineItems} onChange={setLineItems} />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
          <textarea
            rows={3}
            className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm"
            value={form.notes}
            onChange={e => setForm({ ...form, notes: e.target.value })}
          />
        </div>

        <button
          type="submit"
          disabled={createInvoice.isPending}
          className="bg-indigo-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {createInvoice.isPending ? 'Creating...' : 'Create Invoice'}
        </button>
      </form>
    </div>
  )
}
```

---

## `src/pages/InvoiceDetail.jsx`

Shows full invoice detail with:
- Invoice metadata, line item table, total
- **Send button** (only shown for `draft` status) — calls `useSendInvoice()`
- Payment history (list of `payments`)
- Email log timeline (list of `email_logs` from invoice — add to `InvoiceResponse` in backend if not already)
- Status badge

```jsx
import { useParams } from 'react-router-dom'
import { useInvoice, useSendInvoice } from '../api/invoices'

export default function InvoiceDetail() {
  const { id } = useParams()
  const { data: invoice, isLoading } = useInvoice(id)
  const sendInvoice = useSendInvoice()

  if (isLoading) return <div className="p-8 text-gray-400">Loading...</div>
  if (!invoice) return <div className="p-8 text-gray-400">Invoice not found.</div>

  const total = invoice.line_items.reduce(
    (sum, item) => sum + Number(item.quantity) * Number(item.unit_price), 0
  )

  return (
    <div className="p-8 max-w-3xl space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{invoice.invoice_number}</h2>
          <p className="text-sm text-gray-500 mt-1">{invoice.client?.name} — {invoice.client?.company}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-500">
            Due {new Date(invoice.due_date + 'T00:00:00').toLocaleDateString()}
          </span>
          {invoice.status === 'draft' && (
            <button
              onClick={() => sendInvoice.mutate(Number(id))}
              disabled={sendInvoice.isPending}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {sendInvoice.isPending ? 'Sending...' : 'Send Invoice'}
            </button>
          )}
        </div>
      </div>

      {/* Line items */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-200">
              <th className="pb-2">Description</th>
              <th className="pb-2 text-right">Qty</th>
              <th className="pb-2 text-right">Unit Price</th>
              <th className="pb-2 text-right">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {invoice.line_items.map((item, i) => (
              <tr key={i} className="border-b border-gray-100">
                <td className="py-2">{item.description}</td>
                <td className="py-2 text-right">{item.quantity}</td>
                <td className="py-2 text-right">${Number(item.unit_price).toFixed(2)}</td>
                <td className="py-2 text-right">${(Number(item.quantity) * Number(item.unit_price)).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex justify-end mt-3 text-lg font-bold text-gray-900">
          Total: ${total.toFixed(2)}
        </div>
      </div>

      {/* Notes */}
      {invoice.notes && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <p className="text-sm text-gray-500 font-medium mb-1">Notes</p>
          <p className="text-sm text-gray-700">{invoice.notes}</p>
        </div>
      )}
    </div>
  )
}
```

---

## `src/pages/PaymentPortal.jsx`

**Public page** — no auth, no `<Layout />`. Accessed at `/pay/:token`.

Flow:
1. Fetch invoice via `usePublicInvoice(token)` — response includes `stripe_client_secret`
2. Initialize Stripe with `loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY)`
3. Wrap with `<Elements stripe={stripePromise} options={{ clientSecret }}>`
4. Render `<PaymentElement />` inside a form
5. On submit: call `stripe.confirmPayment({ elements, confirmParams: { return_url: window.location.href } })`
6. On return (Stripe redirects back): check URL params `redirect_status=succeeded` → show success state
7. Poll invoice status every 5s while pending (React Query `refetchInterval`) to catch webhook update

```jsx
import { useParams } from 'react-router-dom'
import { loadStripe } from '@stripe/stripe-js'
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { useState } from 'react'
import { usePublicInvoice } from '../api/invoices'

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY)

function CheckoutForm({ invoice }) {
  const stripe = useStripe()
  const elements = useElements()
  const [error, setError] = useState(null)
  const [processing, setProcessing] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!stripe || !elements) return
    setProcessing(true)
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: window.location.href },
    })
    if (error) {
      setError(error.message)
      setProcessing(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <button
        type="submit"
        disabled={!stripe || processing}
        className="w-full bg-indigo-600 text-white py-3 rounded-md font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        {processing ? 'Processing...' : `Pay $${Number(invoice.total).toLocaleString()}`}
      </button>
    </form>
  )
}

export default function PaymentPortal() {
  const { token } = useParams()
  const params = new URLSearchParams(window.location.search)
  const redirectStatus = params.get('redirect_status')

  const { data: invoice, isLoading } = usePublicInvoice(token)

  if (isLoading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>
  if (!invoice) return <div className="min-h-screen flex items-center justify-center text-gray-400">Invoice not found.</div>

  if (redirectStatus === 'succeeded' || invoice.status === 'paid') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-lg border border-gray-200 p-10 text-center max-w-md">
          <div className="text-4xl mb-4">✓</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Payment received!</h2>
          <p className="text-gray-500">Thank you for paying invoice {invoice.invoice_number}.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-lg border border-gray-200 p-8 w-full max-w-lg">
        <h2 className="text-xl font-bold text-gray-900 mb-1">{invoice.invoice_number}</h2>
        <p className="text-sm text-gray-500 mb-6">{invoice.client?.name} — due {new Date(invoice.due_date + 'T00:00:00').toLocaleDateString()}</p>

        {/* Line item summary */}
        <div className="border border-gray-100 rounded-md divide-y divide-gray-100 mb-6">
          {invoice.line_items.map((item, i) => (
            <div key={i} className="flex justify-between px-4 py-2 text-sm">
              <span className="text-gray-700">{item.description} × {item.quantity}</span>
              <span className="font-medium">${(Number(item.quantity) * Number(item.unit_price)).toFixed(2)}</span>
            </div>
          ))}
          <div className="flex justify-between px-4 py-3 font-bold text-gray-900">
            <span>Total</span>
            <span>${Number(invoice.total).toFixed(2)}</span>
          </div>
        </div>

        {invoice.stripe_client_secret ? (
          <Elements stripe={stripePromise} options={{ clientSecret: invoice.stripe_client_secret }}>
            <CheckoutForm invoice={invoice} />
          </Elements>
        ) : (
          <p className="text-sm text-gray-400 text-center">Payment not yet enabled for this invoice.</p>
        )}
      </div>
    </div>
  )
}
```

---

## Local Development

```bash
cd frontend
npm install
cp .env.example .env  # add VITE_API_URL and VITE_STRIPE_PUBLISHABLE_KEY
npm run dev
# App available at http://localhost:5173
```

While backend isn't ready, you can mock API responses by temporarily returning static data in the React Query `queryFn` functions in `src/api/`.

---

## API Contract (from backend)

### `GET /invoices`
```json
[
  {
    "id": 1,
    "client_id": 1,
    "invoice_number": "INV-001",
    "issue_date": "2026-03-03",
    "due_date": "2026-03-23",
    "status": "overdue",
    "token": "550e8400-e29b-41d4-a716-446655440000",
    "line_items": [{"description": "Brand Strategy", "quantity": "1", "unit_price": "2500.00"}],
    "notes": null,
    "total": "2500.00",
    "client": {
      "id": 1, "name": "Alice Johnson", "email": "alice@example.com",
      "company": "Johnson Design", "created_at": "2026-03-01T00:00:00"
    }
  }
]
```

### `GET /invoices/public/{token}`
Same as above plus:
```json
{ "stripe_client_secret": "pi_xxx_secret_yyy" }
```

### `GET /dashboard/summary`
```json
{
  "total_outstanding": "4700.00",
  "total_overdue": "3250.00",
  "total_paid_this_month": "1200.00",
  "invoice_count_by_status": {"draft": 1, "sent": 1, "overdue": 1},
  "cash_flow_forecast": [
    {"date": "2026-04-22", "expected_amount": 1200.0, "invoice_ids": [2]}
  ]
}
```

### `GET /clients`
```json
[{"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "company": "Johnson Design", "created_at": "..."}]
```

---

## Notes

- **Stripe publishable key**: Goes in `frontend/.env` as `VITE_STRIPE_PUBLISHABLE_KEY`. Never use the secret key in the frontend.
- **Invoice total**: Computed by the backend as a `computed_field` on `InvoiceResponse`. Treat it as a read-only field — do not try to POST it.
- **Token routing**: The `/pay/:token` route uses a UUID string, not a numeric ID. The backend `GET /invoices/public/{token}` endpoint is separate from `GET /invoices/{id}`.
- **At-risk indicator**: Computed entirely in the frontend in `InvoiceTable.jsx` — no backend endpoint needed.
- **Auth**: No authentication layer is implemented. Admin routes (`/`, `/invoices`, etc.) are unprotected.

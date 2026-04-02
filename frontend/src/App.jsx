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

import { Routes, Route, Navigate } from 'react-router-dom'
import { Show } from '@clerk/react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import InvoiceDetail from './pages/InvoiceDetail'
import NewInvoice from './pages/NewInvoice'
import Clients from './pages/Clients'
import PaymentPortal from './pages/PaymentPortal'
import SignIn from './pages/SignIn'

function ProtectedLayout() {
  return (
    <>
      <Show when="signed-in">
        <Layout />
      </Show>
      <Show when="signed-out">
        <Navigate to="/sign-in" replace />
      </Show>
    </>
  )
}

export default function App() {
  return (
    <Routes>
      {/* Admin routes — require Clerk sign-in, wrapped in sidebar Layout */}
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/invoices" element={<Invoices />} />
        <Route path="/invoices/new" element={<NewInvoice />} />
        <Route path="/invoices/:id" element={<InvoiceDetail />} />
        <Route path="/clients" element={<Clients />} />
      </Route>

      {/* Auth page */}
      <Route path="/sign-in/*" element={<SignIn />} />

      {/* Public payment portal — no auth, no layout */}
      <Route path="/pay/:token" element={<PaymentPortal />} />
    </Routes>
  )
}

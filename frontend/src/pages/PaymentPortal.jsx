import { useParams } from 'react-router-dom'
import { loadStripe } from '@stripe/stripe-js'
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { useState } from 'react'
import { usePublicInvoice } from '../api/invoices'

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '')

function CheckoutForm({ invoice }) {
  const stripe = useStripe()
  const elements = useElements()
  const [error, setError] = useState(null)
  const [processing, setProcessing] = useState(false)

  const total = invoice.line_items.reduce(
    (sum, item) => sum + Number(item.quantity) * Number(item.unit_price),
    0
  )

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!stripe || !elements) return

    setError(null)
    setProcessing(true)

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: window.location.href,
      },
    })

    // Only reached if there's an immediate error (e.g. card declined)
    if (error) {
      setError(error.message)
      setProcessing(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <button
        type="submit"
        disabled={!stripe || processing}
        className="w-full bg-indigo-600 text-white py-3 rounded-md font-medium text-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {processing
          ? 'Processing payment...'
          : `Pay $${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
      </button>
    </form>
  )
}

function SuccessState({ invoice }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg border border-gray-200 p-10 text-center max-w-md w-full shadow-sm">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Payment received!</h2>
        <p className="text-gray-500 text-sm">
          Thank you for paying invoice <strong>{invoice.invoice_number}</strong>.
          A confirmation has been noted.
        </p>
      </div>
    </div>
  )
}

export default function PaymentPortal() {
  const { token } = useParams()
  const params = new URLSearchParams(window.location.search)
  const redirectStatus = params.get('redirect_status')

  const { data: invoice, isLoading, error } = usePublicInvoice(token)

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm gap-2">
        <span className="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full" />
        Loading invoice...
      </div>
    )
  }

  if (error || !invoice) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-sm text-red-700 text-center max-w-sm">
          <p className="font-medium mb-1">Invoice not found</p>
          <p className="text-red-500">This payment link may be invalid or expired.</p>
        </div>
      </div>
    )
  }

  // Show success if redirected back from Stripe or if invoice is already paid
  if (redirectStatus === 'succeeded' || invoice.status === 'paid') {
    return <SuccessState invoice={invoice} />
  }

  const total = invoice.line_items.reduce(
    (sum, item) => sum + Number(item.quantity) * Number(item.unit_price),
    0
  )

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm w-full max-w-lg">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-100">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Invoice</p>
          <h1 className="text-xl font-bold text-gray-900">{invoice.invoice_number}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            From {invoice.client?.name}
            {invoice.client?.company ? ` · ${invoice.client.company}` : ''}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            Due {new Date(invoice.due_date + 'T00:00:00').toLocaleDateString('en-US', {
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
          </p>
        </div>

        {/* Line items summary */}
        <div className="px-8 py-4 border-b border-gray-100">
          <div className="divide-y divide-gray-100">
            {invoice.line_items.map((item, i) => (
              <div key={i} className="flex justify-between py-2 text-sm">
                <span className="text-gray-700">
                  {item.description}
                  {Number(item.quantity) !== 1 && (
                    <span className="text-gray-400"> × {item.quantity}</span>
                  )}
                </span>
                <span className="font-medium text-gray-900">
                  ${(Number(item.quantity) * Number(item.unit_price)).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
          <div className="flex justify-between pt-3 mt-1 border-t border-gray-200">
            <span className="font-semibold text-gray-900">Total due</span>
            <span className="text-xl font-bold text-gray-900">
              ${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        {/* Payment form */}
        <div className="px-8 py-6">
          {invoice.stripe_client_secret ? (
            <Elements
              stripe={stripePromise}
              options={{
                clientSecret: invoice.stripe_client_secret,
                appearance: {
                  theme: 'stripe',
                  variables: { colorPrimary: '#6366f1' },
                },
              }}
            >
              <CheckoutForm invoice={invoice} />
            </Elements>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">
              Payment has not been enabled for this invoice yet.
            </p>
          )}
        </div>

        <div className="px-8 pb-5 text-center">
          <p className="text-xs text-gray-400">
            Secure payment powered by Stripe. Your card details are never stored.
          </p>
        </div>
      </div>
    </div>
  )
}

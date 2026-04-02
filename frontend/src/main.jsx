import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/react'
import App from './App'
import './index.css'

const clerkPublishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function MissingClerkConfig() {
  return (
    <div className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-xl rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-amber-950">Missing Clerk configuration</h1>
        <p className="mt-3 text-sm leading-6 text-amber-900">
          Set <code>VITE_CLERK_PUBLISHABLE_KEY</code> in <code>frontend/.env</code> and restart the
          Vite dev server.
        </p>
      </div>
    </div>
  )
}

const root = ReactDOM.createRoot(document.getElementById('root'))

root.render(
  <React.StrictMode>
    {clerkPublishableKey ? (
      <ClerkProvider publishableKey={clerkPublishableKey} afterSignOutUrl="/sign-in">
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </ClerkProvider>
    ) : (
      <MissingClerkConfig />
    )}
  </React.StrictMode>
)

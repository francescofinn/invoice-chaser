import { SignIn } from '@clerk/clerk-react'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-indigo-600">Invoice Chaser</h1>
        <p className="text-sm text-gray-500 mt-1">Sign in to manage your invoices</p>
      </div>
      <SignIn routing="path" path="/sign-in" afterSignInUrl="/" />
    </div>
  )
}

import { NavLink, Outlet, Link } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/react'
import { useNavigate } from 'react-router-dom'

function UserSection() {
  const { user } = useUser()
  const { openUserProfile, signOut } = useClerk()
  const navigate = useNavigate()
  const email = user?.emailAddresses?.[0]?.emailAddress || ''
  const name = user?.firstName
    ? `${user.firstName} ${user.lastName || ''}`.trim()
    : email

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => openUserProfile()}
        className="flex items-center gap-2 min-w-0 flex-1 p-2 rounded-lg hover:bg-gray-100 transition-colors text-left"
      >
        <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 overflow-hidden">
          {user?.imageUrl ? (
            <img src={user.imageUrl} alt={name} className="w-full h-full object-cover" />
          ) : (
            <span className="text-xs font-semibold text-indigo-600">
              {(user?.firstName?.[0] || email[0] || '?').toUpperCase()}
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-gray-700 truncate">{name}</p>
          <p className="text-xs text-gray-400 truncate" title={email}>{email}</p>
        </div>
      </button>
      <button
        onClick={() => signOut(() => navigate('/sign-in'))}
        title="Sign out"
        className="shrink-0 p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-gray-100 transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
        </svg>
      </button>
    </div>
  )
}

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/invoices', label: 'Invoices', end: false },
  { to: '/clients', label: 'Clients', end: false },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="px-6 py-5 border-b border-gray-200">
          <Link to="/" className="text-lg font-bold text-indigo-600 hover:text-indigo-700">
            Invoice Chaser
          </Link>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-2 py-3 border-t border-gray-200">
          <UserSection />
        </div>
      </aside>

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}

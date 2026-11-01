import { Link, Outlet } from 'react-router-dom'
import ConsoleBackground from '../components/ConsoleBackground'

// Layout for unauthenticated pages (landing, login, register). Same
// AI-security-console design language as AppShell.
export default function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <ConsoleBackground />
      <header className="border-b border-border-soft">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link to="/" className="flex items-center gap-2.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand">
            <BrandMark />
            <div>
              <div className="font-display text-sm font-semibold tracking-wide text-text">KYC INTELLIGENCE</div>
              <div className="text-[10px] uppercase tracking-wider text-text-faint">AI Identity Verification</div>
            </div>
          </Link>
          <nav className="flex items-center gap-3 text-sm" aria-label="Public navigation">
            <Link to="/login" className="text-text-muted hover:text-text">
              Sign in
            </Link>
            <Link
              to="/register"
              className="rounded-lg bg-brand px-4 py-2 font-medium text-ink transition hover:brightness-110 hover:-translate-y-px hover:shadow-[0_0_20px_-4px_rgba(56,189,248,0.6)]"
            >
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border-soft px-5 py-6 text-center text-xs text-text-faint sm:px-8">
        Academic prototype for a B.Tech final-year project. Not connected to any real Aadhaar, PAN, bank, or
        government database.
      </footer>
    </div>
  )
}

export function BrandMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="24" height="24" rx="7" stroke="#38bdf8" strokeWidth="1.5" />
      <path d="M9 14a5 5 0 0 1 5-5" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="14" cy="14" r="1.6" fill="#22d3ee" />
    </svg>
  )
}

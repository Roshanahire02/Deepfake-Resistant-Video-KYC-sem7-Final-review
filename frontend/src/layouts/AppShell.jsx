import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import ConsoleBackground from '../components/ConsoleBackground'

const USER_GROUPS = [
  {
    heading: 'Command Center',
    links: [
      { to: '/dashboard', label: 'Overview', icon: GridIcon, end: true },
      { to: '/new-kyc', label: 'New Verification', icon: PlusIcon },
      { to: '/cases', label: 'My Cases', icon: FolderIcon },
      { to: '/results', label: 'AI Results', icon: CheckIcon },
    ],
  },
  {
    heading: 'AI Systems',
    links: [
      { to: '/models#face-recognition', label: 'Face Recognition', icon: FaceIcon },
      { to: '/models#liveness', label: 'Liveness', icon: PulseIcon },
      { to: '/models#rppg', label: 'rPPG', icon: WaveIcon },
      { to: '/models#replay-detection', label: 'Replay Detection', icon: ShieldIcon },
      { to: '/models#deepfake', label: 'Deepfake Analysis', icon: ScanIcon },
      { to: '/models#risk-engine', label: 'Risk Engine', icon: GaugeIcon },
    ],
  },
  {
    heading: 'System',
    links: [
      { to: '/models', label: 'Model Status', icon: CpuIcon },
      { to: '/profile', label: 'Profile', icon: UserIcon },
    ],
  },
]

const REVIEWER_GROUPS = [
  {
    heading: 'Command Center',
    links: [
      { to: '/reviewer', label: 'Review Dashboard', icon: GridIcon, end: true },
      { to: '/reviewer/cases', label: 'Cases', icon: FolderIcon },
      { to: '/reviewer/queue', label: 'Review Queue', icon: QueueIcon },
      { to: '/reviewer/reports', label: 'Reports', icon: DocIcon },
    ],
  },
  {
    heading: 'AI Systems',
    links: [
      { to: '/models#face-recognition', label: 'Face Recognition', icon: FaceIcon },
      { to: '/models#liveness', label: 'Liveness', icon: PulseIcon },
      { to: '/models#rppg', label: 'rPPG', icon: WaveIcon },
      { to: '/models#replay-detection', label: 'Replay Detection', icon: ShieldIcon },
      { to: '/models#deepfake', label: 'Deepfake Analysis', icon: ScanIcon },
      { to: '/models#risk-engine', label: 'Risk Engine', icon: GaugeIcon },
    ],
  },
  {
    heading: 'System',
    links: [
      { to: '/models', label: 'Model Status', icon: CpuIcon },
      { to: '/profile', label: 'Profile', icon: UserIcon },
    ],
  },
]

export default function AppShell() {
  const { user, isReviewer, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const baseGroups = isReviewer ? REVIEWER_GROUPS : USER_GROUPS
  const groups = user?.role === 'ADMIN'
    ? [...baseGroups, { heading: 'Administration', links: [{ to: '/admin', label: 'Users & Roles', icon: UserIcon }] }]
    : baseGroups

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const sidebarContent = (
    <>
      <div className="flex items-center gap-2.5 px-5 py-5">
        <BrandMark />
        <div>
          <div className="font-display text-sm font-semibold tracking-wide text-text">KYC INTELLIGENCE</div>
          <div className="text-[10px] uppercase tracking-wider text-text-faint">AI Identity Verification</div>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4" aria-label="Main navigation">
        {groups.map((group) => (
          <div key={group.heading}>
            <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-faint">
              {group.heading}
            </div>
            <div className="space-y-1">
              {group.links.map((l) => {
                const isActive = l.to.includes('#')
                  ? location.pathname === '/models' && location.hash === l.to.slice(l.to.indexOf('#'))
                  : undefined
                return (
                  <NavLink
                    key={l.to}
                    to={l.to}
                    end={l.end}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive: routeActive }) => {
                      const active = isActive !== undefined ? isActive : routeActive
                      return `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand ${
                        active
                          ? 'illuminate bg-brand-soft text-brand'
                          : 'text-text-muted hover:bg-surface-raised hover:text-text'
                      }`
                    }}
                  >
                    <l.icon />
                    {l.label}
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-border-soft p-4">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-brand/30 bg-brand-soft text-xs font-semibold text-brand">
            {(user?.full_name || user?.email || '?').slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-text">{user?.full_name}</div>
            <div className="truncate text-[11px] text-text-faint">{user?.email}</div>
          </div>
          <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-text-muted">
            {user?.role}
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="w-full rounded-lg border border-border px-3 py-2 text-xs text-text-muted transition hover:border-flagged/50 hover:text-flagged focus-visible:outline focus-visible:outline-2 focus-visible:outline-flagged"
        >
          Sign out
        </button>
      </div>
    </>
  )

  return (
    <div className="flex min-h-screen">
      <ConsoleBackground />

      <aside className="hidden w-64 shrink-0 flex-col border-r border-border-soft bg-surface/60 backdrop-blur md:flex">
        {sidebarContent}
      </aside>

      <div className="fixed inset-x-0 top-0 z-40 flex items-center justify-between border-b border-border-soft bg-surface/80 px-4 py-3 backdrop-blur md:hidden">
        <div className="flex items-center gap-2">
          <BrandMark />
          <span className="font-display text-sm font-semibold text-text">KYC INTELLIGENCE</span>
        </div>
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="rounded-md p-2 text-text-muted hover:bg-surface-raised focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        >
          <MenuIcon />
        </button>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="absolute inset-0 bg-black/70" onClick={() => setMobileOpen(false)} aria-hidden="true" />
          <aside className="relative flex w-72 flex-col bg-surface">
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
              className="absolute right-3 top-4 rounded-md p-1.5 text-text-muted hover:bg-surface-raised"
            >
              ✕
            </button>
            {sidebarContent}
          </aside>
        </div>
      )}

      <main className="flex-1 overflow-y-auto pt-14 md:pt-0">
        <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}

function BrandMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="24" height="24" rx="7" stroke="#38bdf8" strokeWidth="1.5" />
      <path d="M9 14a5 5 0 0 1 5-5" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="14" cy="14" r="1.6" fill="#22d3ee" />
    </svg>
  )
}
function MenuIcon() {
  return <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
}
function GridIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><rect x="2" y="2" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" /><rect x="10" y="2" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" /><rect x="2" y="10" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" /><rect x="10" y="10" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" /></svg>
}
function PlusIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
function FolderIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M2 5a1 1 0 0 1 1-1h4l1.5 2H15a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5Z" stroke="currentColor" strokeWidth="1.4" /></svg>
}
function CheckIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.4" /><path d="M6 9.5l2 2 4-4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
}
function CpuIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><rect x="5" y="5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.4" /><path d="M9 1v3M9 14v3M1 9h3M14 9h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
function UserIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><circle cx="9" cy="6" r="3" stroke="currentColor" strokeWidth="1.4" /><path d="M3 16c1-3.3 3.6-5 6-5s5 1.7 6 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
function QueueIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M2 5h14M2 9h14M2 13h9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
function DocIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M5 2h5l3 3v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.4" /><path d="M7 9h4M7 12h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
function FaceIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><rect x="3" y="3" width="12" height="12" rx="3" stroke="currentColor" strokeWidth="1.4" /><circle cx="7" cy="8" r="0.8" fill="currentColor" /><circle cx="11" cy="8" r="0.8" fill="currentColor" /><path d="M7 11.5c.6.6 1.4 1 2 1s1.4-.4 2-1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
}
function PulseIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M2 9h3l1.5-4L10 14l1.5-5H16" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
}
function WaveIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M2 9c1.5-3 2.5-3 4 0s2.5 3 4 0 2.5-3 4 0 2.5 3 4 0" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
function ShieldIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M9 2l6 2v5c0 4-2.5 6.5-6 7-3.5-.5-6-3-6-7V4l6-2Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" /></svg>
}
function ScanIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M3 6V3h3M15 6V3h-3M3 12v3h3M15 12v3h-3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /><path d="M3 9h12" stroke="currentColor" strokeWidth="1.2" strokeDasharray="2 2" /></svg>
}
function GaugeIcon() {
  return <svg width="17" height="17" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M3 13a6 6 0 1 1 12 0" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /><path d="M9 13 12 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}

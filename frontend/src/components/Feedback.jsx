export function LoadingSpinner({ label, size = 'md' }) {
  const dim = { sm: 'h-3.5 w-3.5', md: 'h-4 w-4', lg: 'h-6 w-6' }[size]
  return (
    <div className="flex items-center gap-3 text-sm text-text-muted" role="status" aria-live="polite">
      <span className={`${dim} animate-spin rounded-full border-2 border-border border-t-brand`} aria-hidden="true" />
      {label}
    </div>
  )
}

export function EmptyState({ title, description, action, icon }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16 text-center">
      {icon && <div className="mb-3 text-text-faint">{icon}</div>}
      <h3 className="text-sm font-semibold text-text">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', message, action }) {
  return (
    <div role="alert" className="rounded-xl border border-flagged/30 bg-flagged/5 p-6 text-center">
      <h3 className="text-sm font-semibold text-flagged">{title}</h3>
      {message && <p className="mt-1 text-sm text-text-muted">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// Inline banner variant for form/API errors (smaller than ErrorState).
export function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div role="alert" className="rounded-lg border border-flagged/30 bg-flagged/10 px-4 py-3 text-sm text-flagged">
      {message}
    </div>
  )
}

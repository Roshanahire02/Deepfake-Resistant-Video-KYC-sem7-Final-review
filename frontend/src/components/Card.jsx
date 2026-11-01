export function Card({ children, className = '', as: As = 'div', glow = false, ...props }) {
  return (
    <As
      className={`glass-panel rounded-xl transition-colors duration-200 ${glow ? 'hover:border-brand/40' : ''} ${className}`}
      {...props}
    >
      {children}
    </As>
  )
}

export function CardHeader({ children, className = '' }) {
  return <div className={`flex items-center justify-between border-b border-border-soft px-5 py-4 ${className}`}>{children}</div>
}

export function CardTitle({ children, subtitle, className = '' }) {
  return (
    <div className={className}>
      <h3 className="text-sm font-semibold tracking-wide text-text">{children}</h3>
      {subtitle && <p className="mt-0.5 text-xs text-text-muted">{subtitle}</p>}
    </div>
  )
}

export function CardContent({ children, className = '' }) {
  return <div className={`p-5 ${className}`}>{children}</div>
}

export function CardFooter({ children, className = '' }) {
  return <div className={`border-t border-border-soft px-5 py-4 ${className}`}>{children}</div>
}

// Convenience wrapper for the common case: title/subtitle + body,
// optionally a header-right action.
export function SimpleCard({ title, subtitle, action, children, className = '' }) {
  return (
    <Card className={className}>
      {(title || action) && (
        <CardHeader>
          <CardTitle subtitle={subtitle}>{title}</CardTitle>
          {action}
        </CardHeader>
      )}
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export function StatCard({ label, value, tone = 'neutral', change, icon }) {
  const toneClass = {
    neutral: 'text-text',
    verified: 'text-verified',
    pending: 'text-pending',
    flagged: 'text-flagged',
  }[tone]
  const glowClass = {
    neutral: '',
    verified: 'shadow-[0_0_30px_-12px_rgba(34,197,94,0.35)]',
    pending: 'shadow-[0_0_30px_-12px_rgba(245,158,11,0.35)]',
    flagged: 'shadow-[0_0_30px_-12px_rgba(239,68,68,0.35)]',
  }[tone]
  return (
    <Card className={`p-5 ${glowClass}`}>
      <div className="flex items-start justify-between">
        <div className="text-[11px] font-medium uppercase tracking-wider text-text-faint">{label}</div>
        {icon && <span className="text-text-faint">{icon}</span>}
      </div>
      <div className={`mono mt-2 text-3xl font-semibold ${toneClass}`}>{value}</div>
      {change && <div className="mt-1 text-xs text-text-muted">{change}</div>}
    </Card>
  )
}

const VARIANTS = {
  primary: 'bg-brand text-ink hover:brightness-110 hover:-translate-y-px hover:shadow-[0_0_20px_-4px_rgba(56,189,248,0.6)] focus-visible:outline-brand',
  secondary: 'bg-surface-raised text-text border border-border hover:border-brand/40 hover:-translate-y-px focus-visible:outline-brand',
  outline: 'bg-transparent text-text border border-border hover:bg-surface-raised hover:border-brand/40 focus-visible:outline-brand',
  ghost: 'bg-transparent text-text-muted hover:text-text hover:bg-surface-raised focus-visible:outline-brand',
  danger: 'bg-flagged text-ink hover:brightness-110 hover:-translate-y-px focus-visible:outline-flagged',
  success: 'bg-verified text-ink hover:brightness-110 hover:-translate-y-px focus-visible:outline-verified',
}

const SIZES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-5 py-3 text-base',
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon,
  className = '',
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-150
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2
        disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none
        ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current/30 border-t-current" aria-hidden="true" />
      ) : (
        icon && <span aria-hidden="true">{icon}</span>
      )}
      {children}
    </button>
  )
}

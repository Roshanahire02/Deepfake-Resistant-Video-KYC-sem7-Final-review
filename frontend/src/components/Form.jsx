export function Field({ label, children, hint, error }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-text-muted">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-flagged">{error}</span>
      ) : (
        hint && <span className="mt-1 block text-xs text-text-faint">{hint}</span>
      )}
    </label>
  )
}

export function Input(props) {
  return (
    <input
      className="w-full rounded-lg border border-border bg-ink px-3 py-2.5 text-sm text-text placeholder:text-text-faint focus:border-brand focus:outline-none"
      {...props}
    />
  )
}

export function Select({ children, ...props }) {
  return (
    <select
      className="w-full rounded-lg border border-border bg-ink px-3 py-2.5 text-sm text-text focus:border-brand focus:outline-none"
      {...props}
    >
      {children}
    </select>
  )
}

export function Checkbox({ label, ...props }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-sm text-text">
      <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border-border bg-ink accent-[#2dd4bf]" {...props} />
      <span>{label}</span>
    </label>
  )
}

import { useEffect } from 'react'

export default function Modal({ open, onClose, title, children, footer }) {
  useEffect(() => {
    if (!open) return
    function onKey(e) {
      if (e.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-md rounded-xl border border-border bg-surface shadow-xl">
        <div className="flex items-center justify-between border-b border-border-soft px-5 py-4">
          <h3 className="text-sm font-semibold text-text">{title}</h3>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-md p-1 text-text-muted hover:bg-surface-raised hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          >
            ✕
          </button>
        </div>
        <div className="p-5">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-border-soft px-5 py-4">{footer}</div>}
      </div>
    </div>
  )
}

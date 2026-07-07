// Layered browser-frame wrapper for product screenshots, à la the Sana reference.
export default function DeviceFrame({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-border bg-surface shadow-2xl shadow-black/40 overflow-hidden ${className}`}
    >
      <div className="flex items-center gap-1.5 border-b border-border bg-surface-2 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
      </div>
      <div className="relative">{children}</div>
    </div>
  )
}

// Solana is intentionally parked (see TODO.md "Parked / Not in Scope") —
// shown here as a roadmap item, not claimed as currently supported. Keeping
// it visible (distinctly styled) rather than deleting it preserves the
// forward-looking scope without overclaiming what actually works today.
const CHAINS = [
  { name: 'EVM', status: 'active' },
  { name: 'Solana', status: 'planned' },
]

export default function ChainSupport() {
  return (
    <section id="chains" className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
            Chain support
          </p>
          <div className="flex items-center gap-3">
            {CHAINS.map((chain) =>
              chain.status === 'active' ? (
                <span
                  key={chain.name}
                  className="rounded-full border border-border px-4 py-1.5 text-sm font-medium text-ink/80"
                >
                  {chain.name}
                </span>
              ) : (
                <span
                  key={chain.name}
                  className="flex items-center gap-1.5 rounded-full border border-dashed border-border/60 px-4 py-1.5 text-sm font-medium text-muted"
                >
                  {chain.name}
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted/70">
                    Planned
                  </span>
                </span>
              )
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

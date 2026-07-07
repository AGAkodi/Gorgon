const CHAINS = ['EVM', 'Solana']

export default function ChainSupport() {
  return (
    <section id="chains" className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
            Chain support
          </p>
          <div className="flex items-center gap-3">
            {CHAINS.map((chain) => (
              <span
                key={chain}
                className="rounded-full border border-border px-4 py-1.5 text-sm font-medium text-ink/80"
              >
                {chain}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

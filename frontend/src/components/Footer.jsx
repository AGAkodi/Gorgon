import { Link } from 'react-router-dom'
import { ShieldHalf } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Link to="/" className="flex items-center gap-2">
              <ShieldHalf size={20} strokeWidth={2.25} />
              <span className="font-display text-base font-bold tracking-tight">Vetra</span>
            </Link>
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted">
              Programmable trust infrastructure for the agent economy.
            </p>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted">Product</p>
            <ul className="mt-4 space-y-2.5 text-sm text-ink/80">
              <li><Link to="/dashboard" className="hover:text-ink">Verdict Engine</Link></li>
              <li><Link to="/sandbox" className="hover:text-ink">Simulation Sandbox</Link></li>
              <li><Link to="/#pricing" className="hover:text-ink">Pricing</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted">Developers</p>
            <ul className="mt-4 space-y-2.5 text-sm text-ink/80">
              <li><Link to="/#developers" className="hover:text-ink">MCP Tools</Link></li>
              <li><Link to="/#developers" className="hover:text-ink">Docs</Link></li>
              <li><Link to="/#chains" className="hover:text-ink">Chain Support</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted">Company</p>
            <ul className="mt-4 space-y-2.5 text-sm text-ink/80">
              <li><Link to="/" className="hover:text-ink">About</Link></li>
              <li><Link to="/" className="hover:text-ink">Contact</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-border pt-6 sm:flex-row sm:items-center">
          <p className="text-xs text-muted">© 2026 Vetra. Verdicts are risk signals, not guarantees.</p>
          <span className="inline-flex items-center rounded-full border border-border px-3 py-1.5 text-xs font-medium text-ink/80">
            Listed on OKX.AI
          </span>
        </div>
      </div>
    </footer>
  )
}

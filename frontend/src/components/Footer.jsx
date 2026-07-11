import { Link } from 'react-router-dom'
import { ShieldHalf } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface/50">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Link to="/" className="flex items-center gap-2 group">
              <div className="w-7 h-7 rounded-full bg-brand flex items-center justify-center text-bg group-hover:scale-105 transition-transform">
                <ShieldHalf size={15} strokeWidth={2.5} />
              </div>
              <span className="font-display text-base font-extrabold tracking-tight text-ink">Vetra</span>
            </Link>
            <p className="mt-3 max-w-xs text-xs leading-relaxed text-muted">
              Programmable trust infrastructure and transaction auditing for the agentic web.
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Product</p>
            <ul className="mt-4 space-y-2.5 text-xs font-semibold text-muted">
              <li><Link to="/dashboard" className="hover:text-brand transition-colors">Verdict Engine</Link></li>
              <li><Link to="/sandbox" className="hover:text-brand transition-colors">Simulation Sandbox</Link></li>
              <li><Link to="/pricing" className="hover:text-brand transition-colors">Pricing Panel</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Developers</p>
            <ul className="mt-4 space-y-2.5 text-xs font-semibold text-muted">
              <li><Link to="/api-keys" className="hover:text-brand transition-colors">API Credentials</Link></li>
              <li><Link to="/#features" className="hover:text-brand transition-colors">Core Modules</Link></li>
              <li><Link to="/#chains" className="hover:text-brand transition-colors">Chain Support</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Company</p>
            <ul className="mt-4 space-y-2.5 text-xs font-semibold text-muted">
              <li><Link to="/" className="hover:text-brand transition-colors">About Vetra</Link></li>
              <li><Link to="/" className="hover:text-brand transition-colors">Contact</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-border pt-6 sm:flex-row sm:items-center">
          <p className="text-xs text-muted">© 2026 Vetra. Verdicts are risk signals, not financial guarantees.</p>
          <span className="inline-flex items-center rounded-full border border-brand/20 bg-brand/5 px-3.5 py-1.5 text-xs font-bold text-brand uppercase tracking-wider">
            Listed on OKX.AI
          </span>
        </div>
      </div>
    </footer>
  )
}

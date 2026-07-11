import { Coins, CircleHelp, ExternalLink } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import PillButton from '../components/PillButton'
import { Link } from 'react-router-dom'

export default function PricingPreview() {
  const { isConnected, triggerLogin } = useAuth()

  return (
    <section id="pricing" className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
              Flat Rates
            </p>
            <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              Pay strictly for what you verify.
            </h2>
            <p className="mt-4 text-sm text-muted max-w-md leading-relaxed">
              Vetra provides developers and agent runners with complete cost transparency. There are no monthly base fees, setup costs, or premium subscription gates.
            </p>
            <div className="mt-6">
              {isConnected ? (
                <Link
                  to="/pricing"
                  className="inline-flex items-center gap-1.5 font-display text-xs font-bold text-brand uppercase tracking-wider hover:underline"
                >
                  View full billing details
                  <ExternalLink size={14} />
                </Link>
              ) : (
                <button
                  onClick={triggerLogin}
                  className="inline-flex items-center gap-1.5 font-display text-xs font-bold text-brand uppercase tracking-wider hover:underline cursor-pointer bg-transparent border-0 p-0"
                >
                  Connect wallet to view pricing table
                  <ExternalLink size={14} />
                </button>
              )}
            </div>
          </div>

          <div className="rounded-3xl border-2 border-border bg-surface p-8 relative overflow-hidden shadow-xl">
            {/* Curved background line decoration */}
            <div className="absolute top-0 right-0 w-24 h-24 border-l border-b border-border/40 rounded-bl-[40px] pointer-events-none" />

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full border border-border bg-bg flex items-center justify-center text-brand">
                <Coins size={18} />
              </div>
              <div>
                <h4 className="font-display font-bold text-base text-ink">Pay-Per-Call Summary</h4>
                <p className="text-xs text-muted">Billed natively via USDC on X Layer</p>
              </div>
            </div>

            <hr className="my-6 border-border/80" />

            <div className="space-y-4">
              <div className="flex justify-between items-center text-sm">
                <span className="font-mono text-xs text-muted">get_security_verdict</span>
                <span className="font-display font-bold text-ink">0.005 USDC <span className="text-[10px] font-normal font-sans text-muted">/ call</span></span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="font-mono text-xs text-muted">simulate_wallet_interaction</span>
                <span className="font-display font-bold text-ink">0.020 USDC <span className="text-[10px] font-normal font-sans text-muted">/ call</span></span>
              </div>
            </div>

            <div className="mt-8">
              {!isConnected ? (
                <PillButton as="button" onClick={triggerLogin} variant="primary" className="w-full justify-center">
                  Sign in to Pre-fund Wallet
                </PillButton>
              ) : (
                <PillButton to="/pricing" variant="secondary" className="w-full justify-center">
                  Access Billing Console
                </PillButton>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

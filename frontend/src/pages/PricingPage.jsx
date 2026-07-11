import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import PillButton from '../components/PillButton'
import { Coins, CircleHelp, ShieldCheck } from 'lucide-react'

export default function PricingPage() {
  const { isConnected, triggerLogin } = useAuth()
  const [rates, setRates] = useState({ verdict_price: 10, simulation_price: 20 })

  const fetchPricing = async () => {
    try {
      const resp = await fetch('http://localhost:4023/api/pricing')
      if (resp.ok) {
        const data = await resp.json()
        setRates(data)
      }
    } catch (err) {
      console.error('Failed to fetch pricing rates:', err)
    }
  }

  useEffect(() => {
    fetchPricing()
  }, [])

  const pricingRows = [
    {
      endpoint: 'get_security_verdict',
      desc: 'Queries the static analyzer, consensus models, DeFi exploit database, and attests on-chain.',
      cost: `${rates.verdict_price} vUSD`,
      unit: 'per contract / link scan'
    },
    {
      endpoint: 'simulate_wallet_interaction',
      desc: 'Spawns an isolated sandbox to run impersonated decoy transactions against an EVM fork.',
      cost: `${rates.simulation_price} vUSD`,
      unit: 'per simulated interaction'
    }
  ]

  if (!isConnected) {
    return (
      <div className="min-h-screen bg-bg text-ink flex flex-col justify-between">
        <Nav />
        <main className="flex-1 flex items-center justify-center px-6 py-20">
          <div className="max-w-md w-full rounded-3xl border-2 border-border bg-surface p-8 text-center shadow-xl relative overflow-hidden">
            <div className="absolute -top-3 -right-3 w-6 h-6 border border-border bg-bg rotate-45" />
            <div className="absolute -bottom-3 -left-3 w-6 h-6 border border-border bg-bg rotate-45" />

            <div className="mx-auto w-12 h-12 rounded-full border border-border bg-bg flex items-center justify-center text-brand mb-4">
              <Coins size={24} />
            </div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">Access Gated</h2>
            <p className="mt-3 text-sm text-muted leading-relaxed">
              Vetra's pay-per-call developer billing panel is connected directly to your wallet account. Please sign in via SIWE to view.
            </p>
            <div className="mt-6">
              <PillButton as="button" onClick={triggerLogin} variant="primary" className="w-full">
                Connect Wallet
              </PillButton>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col justify-between">
      <Nav />
      <main className="flex-grow mx-auto max-w-4xl w-full px-6 py-14">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          Transparent Billing
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          Pay-Per-Call Rates
        </h1>
        <p className="mt-2 text-sm text-muted">
          No monthly tiers or hidden fees. Billing is calculated strictly on a per-call basis, settled directly on X Layer via x402 micro-transactions.
        </p>

        {/* Pricing Table Card */}
        <div className="mt-8 rounded-3xl border border-border bg-surface overflow-hidden">
          <div className="px-6 py-5 border-b border-border">
            <h3 className="font-display text-base font-bold tracking-tight">Developer API Costs</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-2/40 text-[10px] font-semibold uppercase tracking-wider text-muted">
                  <th className="px-6 py-3.5">Endpoint/Tool</th>
                  <th className="px-6 py-3.5">Description</th>
                  <th className="px-6 py-3.5 text-right">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {pricingRows.map((row) => (
                  <tr key={row.endpoint} className="text-sm hover:bg-surface-2/30 transition-colors">
                    <td className="px-6 py-5 font-mono text-xs font-semibold text-brand">
                      {row.endpoint}
                    </td>
                    <td className="px-6 py-5 text-muted leading-relaxed max-w-sm">
                      {row.desc}
                    </td>
                    <td className="px-6 py-5 text-right">
                      <div className="font-display font-bold text-ink whitespace-nowrap">
                        {row.cost}
                      </div>
                      <div className="text-[10px] text-muted whitespace-nowrap">
                        {row.unit}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Info Grid */}
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <h4 className="font-display font-bold text-sm text-ink flex items-center gap-2">
              <ShieldCheck className="text-brand" size={16} />
              On-Chain Settlement
            </h4>
            <p className="text-xs text-muted leading-relaxed mt-2">
              Verdicts and logs settle on X Layer testnet. Gas for attestation publishes is included inside the call rates—you only pay the flat per-call fee.
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <h4 className="font-display font-bold text-sm text-ink flex items-center gap-2">
              <CircleHelp className="text-brand" size={16} />
              Wallet Pre-Funding
            </h4>
            <p className="text-xs text-muted leading-relaxed mt-2">
              Vetra checks your wallet balance prior to running queries. If your balance on X Layer falls below the cost of the requested endpoint, queries will fail gracefully.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}


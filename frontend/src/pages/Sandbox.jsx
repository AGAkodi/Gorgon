import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, TrendingDown, ShieldCheck } from 'lucide-react'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import PillButton from '../components/PillButton'
import DeviceFrame from '../components/DeviceFrame'
import VerdictChip from '../components/VerdictChip'
import { useCountTo } from '../lib/useCountTo'

const MOCK_APPROVALS = [
  { spender: '0x00f2...dra1n', asset: 'USDC', amount: 'unlimited', unlimited: true, known_drainer: true },
  { spender: '0x4a91...c02b', asset: 'WETH', amount: '0.00', unlimited: false, known_drainer: false },
]

const MOCK_BALANCE_DELTAS = [
  { asset: 'ETH', amount: '-2.48', usd_value: -6820 },
  { asset: 'USDC', amount: '-1,200.00', usd_value: -1200 },
]

const cardMotion = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

function Card({ title, children }) {
  return (
    <motion.div
      initial="hidden"
      animate="show"
      exit="hidden"
      variants={cardMotion}
      className="rounded-2xl border border-border bg-surface p-6"
    >
      <h3 className="font-display text-base font-bold tracking-tight">{title}</h3>
      <div className="mt-4">{children}</div>
    </motion.div>
  )
}

function BalanceDeltaRow({ asset, amount, usdValue }) {
  const animated = useCountTo(usdValue, { duration: 1200, delay: 200 })
  const negative = usdValue < 0
  return (
    <div className="flex items-center justify-between rounded-xl bg-surface-2 px-4 py-3">
      <span className="font-mono text-sm text-ink/80">{asset}</span>
      <div className="flex items-center gap-3 font-mono text-sm">
        <span className={negative ? 'text-verdict-critical' : 'text-verdict-safe'}>{amount}</span>
        <span className="text-xs text-muted">
          ${Math.round(animated).toLocaleString()}
        </span>
      </div>
    </div>
  )
}

export default function Sandbox() {
  const [target, setTarget] = useState('0x4d2a...sign — claim() call')
  const [status, setStatus] = useState('idle')
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (status !== 'running') return undefined
    const timers = [1, 2, 3].map((n) =>
      setTimeout(() => {
        setStep(n)
        if (n === 3) setStatus('done')
      }, n * 700),
    )
    return () => timers.forEach(clearTimeout)
  }, [status])

  const handleSubmit = (e) => {
    e.preventDefault()
    setStatus('running')
    setStep(0)
  }

  return (
    <div className="min-h-screen bg-bg text-ink">
      <Nav />

      <main className="mx-auto max-w-4xl px-6 py-14">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verdict-critical">
          Simulate
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          Simulation Sandbox
        </h1>

        <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-verdict-caution/30 bg-verdict-caution/10 px-4 py-2 text-xs font-medium text-verdict-caution">
          <FlaskConical size={14} />
          Simulated, isolated environment — no real funds or live wallets are ever touched
        </div>

        <form
          onSubmit={handleSubmit}
          className="mt-8 flex flex-col items-stretch gap-3 rounded-full border border-border bg-surface p-2 sm:flex-row sm:items-center"
        >
          <div className="flex flex-1 items-center gap-2 rounded-full px-4 py-2">
            <input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Contract address + method, or decoded payload"
              className="w-full bg-transparent font-mono text-sm text-ink outline-none placeholder:text-muted"
            />
          </div>
          <PillButton as="button" type="submit" variant="primary" disabled={status === 'running'}>
            {status === 'running' ? 'Simulating…' : 'Simulate'}
          </PillButton>
        </form>

        <div className="mt-8">
          <DeviceFrame>
            <div className="bg-bg p-6">
              <div className="flex items-center justify-between font-mono text-xs text-muted">
                <span>decoy wallet · 0x0d3c...f001</span>
                <span>chain: evm</span>
              </div>

              <div className="mt-6 space-y-6">
                <AnimatePresence>
                  {step >= 1 && (
                    <Card key="approvals" title="Approvals granted">
                      <ul className="space-y-2.5">
                        {MOCK_APPROVALS.map((a) => (
                          <li key={a.spender} className="flex items-center justify-between text-sm">
                            <span className="font-mono text-ink/80">{a.spender}</span>
                            <span className="flex items-center gap-2 font-mono text-xs">
                              <span className="text-muted">{a.asset}</span>
                              <span className={a.unlimited ? 'text-verdict-critical' : 'text-verdict-safe'}>
                                {a.amount}
                              </span>
                              {a.known_drainer && (
                                <span className="rounded-full bg-verdict-critical/10 px-2 py-0.5 text-verdict-critical">
                                  known drainer
                                </span>
                              )}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </Card>
                  )}

                  {step >= 2 && (
                    <Card key="balances" title="Balance changes">
                      <div className="space-y-2.5">
                        {MOCK_BALANCE_DELTAS.map((b) => (
                          <BalanceDeltaRow
                            key={b.asset}
                            asset={b.asset}
                            amount={b.amount}
                            usdValue={b.usd_value}
                          />
                        ))}
                      </div>
                    </Card>
                  )}

                  {step >= 3 && (
                    <Card key="risk" title="Risk summary">
                      <div className="flex items-center justify-between">
                        <p className="max-w-sm text-sm text-muted">
                          Unlimited USDC approval to a known drainer address, combined with an
                          immediate balance outflow, indicates an active drain pattern.
                        </p>
                        <VerdictChip verdict="critical" size="lg" />
                      </div>
                    </Card>
                  )}
                </AnimatePresence>

                {status !== 'done' && step === 0 && (
                  <div className="flex items-center gap-2 py-6 text-sm text-muted">
                    <ShieldCheck size={16} />
                    Run a simulation to see the staged wallet impact report.
                  </div>
                )}
              </div>
            </div>
          </DeviceFrame>
        </div>
      </main>

      <Footer />
    </div>
  )
}

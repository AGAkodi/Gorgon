import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Hash, ExternalLink } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, ResponsiveContainer } from 'recharts'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import PillButton from '../components/PillButton'
import VerdictChip from '../components/VerdictChip'
import { VERDICTS } from '../lib/verdict'

const MOCK_STATIC_FINDINGS = [
  { rule: 'Unchecked external call', severity: 'medium', location: 'withdraw() L142' },
  { rule: 'Reentrancy guard missing', severity: 'high', location: 'claim() L88' },
  { rule: 'Owner-only pause', severity: 'info', location: 'pause() L21' },
]

const MOCK_CONSENSUS = [
  { model: 'Claude', risk_category: 'safe', rationale: 'No unsafe external calls reachable from user input.', confidence: 0.95 },
  { model: 'GPT-4', risk_category: 'safe', rationale: 'Static findings are guarded by existing modifiers.', confidence: 0.9 },
  { model: 'Consensus-3', risk_category: 'caution', rationale: 'Reentrancy guard absent on claim(); flagged as a signal, not averaged away.', confidence: 0.62 },
]

const MOCK_EXPLOIT_MATCHES = [
  { known_incident: 'SWC-107 Reentrancy pattern', similarity_score: 0.34 },
  { known_incident: 'DeFiHackLabs — vault drain 2023', similarity_score: 0.18 },
]

const MOCK_ATTESTATION = {
  tx_hash: '0x9e21...4b0f',
  chain: 'X Layer testnet',
  timestamp: new Date().toISOString(),
  verdict_hash: '0x5c7a...e912',
}

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

const severityColor = {
  info: 'text-muted',
  low: 'text-verdict-safe',
  medium: 'text-verdict-caution',
  high: 'text-verdict-high_risk',
  critical: 'text-verdict-critical',
}

export default function Dashboard() {
  const [address, setAddress] = useState('0x7a3f1c9b2d4e5f60718293a4b5c6d7e8f9190123')
  const [chain, setChain] = useState('evm')
  const [status, setStatus] = useState('idle')
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (status !== 'running') return undefined
    const timers = [1, 2, 3, 4].map((n) =>
      setTimeout(() => {
        setStep(n)
        if (n === 4) setStatus('done')
      }, n * 650),
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
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Verdict Engine
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          Verdict Dashboard
        </h1>

        <form
          onSubmit={handleSubmit}
          className="mt-8 flex flex-col items-stretch gap-3 rounded-full border border-border bg-surface p-2 sm:flex-row sm:items-center"
        >
          <div className="flex flex-1 items-center gap-2 rounded-full px-4 py-2">
            <Search size={16} className="shrink-0 text-muted" />
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Contract address or program ID"
              className="w-full bg-transparent font-mono text-sm text-ink outline-none placeholder:text-muted"
            />
          </div>
          <select
            value={chain}
            onChange={(e) => setChain(e.target.value)}
            className="rounded-full border border-border bg-surface-2 px-4 py-2 text-sm text-ink outline-none"
          >
            <option value="evm">EVM</option>
            <option value="solana">Solana</option>
          </select>
          <PillButton as="button" type="submit" variant="primary" disabled={status === 'running'}>
            {status === 'running' ? 'Analyzing…' : 'Get Verdict'}
          </PillButton>
        </form>

        {/* Threat Intelligence Flywheel Metrics */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-border bg-surface/50 px-5 py-4 backdrop-blur-xs">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Exploit Signatures</p>
            <h4 className="mt-2 font-display text-2xl font-bold text-ink">100</h4>
            <p className="mt-1 text-[11px] text-muted">DeFi incident database</p>
          </div>
          <div className="rounded-2xl border border-border bg-surface/50 px-5 py-4 backdrop-blur-xs">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Autonomous Growth</p>
            <h4 className="mt-2 font-display text-2xl font-bold text-verdict-safe">+8.5%</h4>
            <p className="mt-1 text-[11px] text-muted">Sandbox auto-additions</p>
          </div>
          <div className="rounded-2xl border border-border bg-surface/50 px-5 py-4 backdrop-blur-xs">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Blocked Addresses</p>
            <h4 className="mt-2 font-display text-2xl font-bold text-ink">138</h4>
            <p className="mt-1 text-[11px] text-muted">Threat registry size</p>
          </div>
        </div>

        {status === 'done' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 flex items-center justify-between rounded-2xl border border-border bg-surface p-6"
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                Overall verdict
              </p>
              <p className="mt-1 text-sm text-muted">{address.slice(0, 10)}…{address.slice(-4)}</p>
            </div>
            <VerdictChip verdict="caution" size="lg" />
          </motion.div>
        )}

        <div className="mt-6 space-y-6">
          <AnimatePresence>
            {step >= 1 && (
              <Card key="static" title="Static findings">
                <ul className="space-y-2.5">
                  {MOCK_STATIC_FINDINGS.map((f) => (
                    <li key={f.rule} className="flex items-center justify-between text-sm">
                      <span className="text-ink/85">{f.rule}</span>
                      <span className="flex items-center gap-3 font-mono text-xs text-muted">
                        {f.location}
                        <span className={`uppercase ${severityColor[f.severity]}`}>{f.severity}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {step >= 2 && (
              <Card key="consensus" title="Model consensus">
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={MOCK_CONSENSUS} layout="vertical" margin={{ left: 8, right: 16 }}>
                      <CartesianGrid horizontal={false} stroke="var(--color-border)" />
                      <XAxis type="number" domain={[0, 1]} hide />
                      <YAxis
                        type="category"
                        dataKey="model"
                        width={90}
                        tick={{ fill: 'var(--color-muted)', fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Bar dataKey="confidence" radius={[0, 6, 6, 0]} barSize={14}>
                        {MOCK_CONSENSUS.map((entry) => (
                          <Cell key={entry.model} fill={VERDICTS[entry.risk_category].color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <ul className="mt-2 space-y-2">
                  {MOCK_CONSENSUS.map((m) => (
                    <li key={m.model} className="text-sm text-muted">
                      <span className="font-medium text-ink/85">{m.model}:</span> {m.rationale}
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {step >= 3 && (
              <Card key="exploit" title="Exploit matches">
                <ul className="space-y-2.5">
                  {MOCK_EXPLOIT_MATCHES.map((m) => (
                    <li key={m.known_incident} className="flex items-center justify-between text-sm">
                      <span className="text-ink/85">{m.known_incident}</span>
                      <span className="font-mono text-xs text-muted">
                        similarity {Math.round(m.similarity_score * 100)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {step >= 4 && (
              <Card key="attestation" title="Attestation">
                <div className="flex flex-col gap-2 font-mono text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
                  <span className="flex items-center gap-2">
                    <Hash size={14} />
                    {MOCK_ATTESTATION.verdict_hash}
                  </span>
                  <a href="#" className="inline-flex items-center gap-1.5 text-ink/80 hover:text-ink">
                    View on {MOCK_ATTESTATION.chain}
                    <ExternalLink size={13} />
                  </a>
                </div>
              </Card>
            )}
          </AnimatePresence>
        </div>
      </main>

      <Footer />
    </div>
  )
}

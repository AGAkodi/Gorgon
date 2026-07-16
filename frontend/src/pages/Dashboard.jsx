import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Hash, ExternalLink, ShieldAlert, Cpu, Eye, CheckCircle2, AlertTriangle, ShieldCheck, ChevronDown, Code2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, ResponsiveContainer } from 'recharts'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import PillButton from '../components/PillButton'
import VerdictChip from '../components/VerdictChip'
import { VERDICTS, VERDICT_ORDER } from '../lib/verdict'
import { useAuth } from '../context/AuthContext'
import { API_BASE_URL } from '../lib/api'

const MOCK_STATIC_FINDINGS = {
  safe: [],
  caution: [
    { rule: 'Reentrancy guard missing', severity: 'medium', location: 'claim() L88' },
    { rule: 'Unchecked return value', severity: 'low', location: 'transfer() L142' }
  ],
  high_risk: [
    { rule: 'Direct transfer of contract ownership', severity: 'high', location: 'transferOwnership() L44' },
    { rule: 'Use of tx.origin for authentication', severity: 'high', location: 'isAuthorized() L52' }
  ],
  critical: [
    { rule: 'Unlimited token approvals requested', severity: 'critical', location: 'approve() L105' },
    { rule: 'Selfdestruct callable by anyone', severity: 'critical', location: 'kill() L210' }
  ]
}

const MOCK_CONSENSUS = {
  safe: [
    { model: 'Claude', risk_category: 'safe', rationale: 'Logic matches standard ERC20 interface. No vulnerable paths detected.', confidence: 0.98 },
    { model: 'GPT-4', risk_category: 'safe', rationale: 'Static validation passes. Safe execution path verified.', confidence: 0.95 }
  ],
  caution: [
    { model: 'Claude', risk_category: 'caution', rationale: 'Missing reentrancy guard on claim(). High congestion might cause state race.', confidence: 0.75 },
    { model: 'GPT-4', risk_category: 'safe', rationale: 'Code path is standard but missing state check modifiers.', confidence: 0.6 }
  ],
  high_risk: [
    { model: 'Claude', risk_category: 'high_risk', rationale: 'Direct transfer of ownership is vulnerable to transaction front-running.', confidence: 0.88 },
    { model: 'GPT-4', risk_category: 'caution', rationale: 'Front-running vectors identified during ownership shifts.', confidence: 0.72 }
  ],
  critical: [
    { model: 'Claude', risk_category: 'critical', rationale: 'Vulnerable token approval layout allows spenders to drain account balance.', confidence: 0.96 },
    { model: 'GPT-4', risk_category: 'critical', rationale: 'Selfdestruct call is exposed to the public. Critical threat.', confidence: 0.92 }
  ]
}

const MOCK_EXPLOIT_MATCHES = {
  safe: [],
  caution: [
    { known_incident: 'SWC-107 Reentrancy pattern', similarity_score: 0.42 }
  ],
  high_risk: [
    { known_incident: 'SWC-105 Unprotected ownership', similarity_score: 0.78 }
  ],
  critical: [
    { known_incident: 'ERC-20 unlimited approval abuse', similarity_score: 0.94 },
    { known_incident: 'Parity multisig vulnerability pattern', similarity_score: 0.82 }
  ]
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
      className="rounded-3xl border border-border bg-surface p-6"
    >
      <h3 className="font-display text-sm font-bold tracking-tight text-ink uppercase">{title}</h3>
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

const verdictConcerns = {
  safe: '',
  caution: 'This contract is missing a reentrancy guard on claim() which may result in minor reward manipulation.',
  high_risk: 'This contract allows direct ownership transfer without multi-sig authentication.',
  critical: 'This contract requests unlimited token approvals and contains a public selfdestruct method.',
}

export default function Dashboard() {
  const { isConnected, triggerLogin, walletAddress } = useAuth()
  const navigate = useNavigate()

  const [address, setAddress] = useState('0x1F98431c8aD98523631AE4a59f267346ea31F984')
  const [type, setType] = useState('contract') // contract or link
  const [status, setStatus] = useState('idle')
  const [step, setStep] = useState(0)
  const [showPopup, setShowPopup] = useState(false)

  // No block-explorer source-fetching integration exists yet, so without
  // this the static analyzer always sees an empty source and correctly
  // reports insufficient_data -> caution, regardless of what address is
  // typed above. Paste real source here to actually exercise the analyzer.
  const [sourceCode, setSourceCode] = useState('')
  const [showSourceInput, setShowSourceInput] = useState(false)

  // Real audit state
  const [verdict, setVerdict] = useState('safe')
  const [staticFindings, setStaticFindings] = useState([])
  const [modelConsensus, setModelConsensus] = useState([])
  const [exploitMatches, setExploitMatches] = useState([])
  const [attestationTxHash, setAttestationTxHash] = useState('')
  const [cacheHit, setCacheHit] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('running')
    setStep(0)
    setShowPopup(false)

    // Clear any result from a previous run so a failed/in-flight request can
    // never display leftover data under the step-gated cards below.
    setVerdict('')
    setStaticFindings([])
    setModelConsensus([])
    setExploitMatches([])
    setAttestationTxHash('')
    setCacheHit(false)

    // Step interval animation triggers — must be cancelled on failure too,
    // otherwise they keep firing on their own schedule and re-reveal the
    // step-gated cards after the catch block below has already reset step to 0.
    const t1 = setTimeout(() => setStep(1), 800)
    const t2 = setTimeout(() => setStep(2), 1600)
    const t3 = setTimeout(() => setStep(3), 2400)

    try {
      const token = localStorage.getItem('vetra_session_token')
      const resp = await fetch(`${API_BASE_URL}/api/audit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          chain: 'evm',
          address: address.trim(),
          source_code: sourceCode.trim()
        })
      })

      if (!resp.ok) {
        throw new Error(await resp.text())
      }

      const data = await resp.json()

      // Clear interval animations and complete step progression
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)

      setVerdict(data.verdict)
      setStaticFindings(data.static_findings || [])
      setModelConsensus(data.model_consensus || [])
      setExploitMatches(data.exploit_matches || [])
      setAttestationTxHash(data.attestation?.tx_hash || '')
      setCacheHit(data.cache_hit || false)

      setStep(4)
      setStatus('done')

      if (data.verdict !== 'safe') {
        setShowPopup(true)
      }
    } catch (err) {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      console.error('Audit run failure:', err)
      alert(err.message || 'Failed to complete security audit.')
      setStatus('idle')
      setStep(0)
    }
  }

  const handleTryInSandbox = () => {
    setShowPopup(false)
    navigate('/sandbox', {
      state: {
        target: address,
        type: type,
        verdict: verdict,
      },
    })
  }

  if (!isConnected) {
    return (
      <div className="min-h-screen bg-bg text-ink flex flex-col justify-between">
        <Nav />
        <main className="flex-grow flex items-center justify-center px-6 py-20">
          <div className="max-w-md w-full rounded-3xl border-2 border-border bg-surface p-8 text-center shadow-xl relative overflow-hidden">
            <div className="absolute -top-3 -right-3 w-6 h-6 border border-border bg-bg rotate-45" />
            <div className="absolute -bottom-3 -left-3 w-6 h-6 border border-border bg-bg rotate-45" />

            <div className="mx-auto w-12 h-12 rounded-full border border-border bg-bg flex items-center justify-center text-brand mb-4">
              <Cpu size={24} />
            </div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">Access Gated</h2>
            <p className="mt-3 text-sm text-muted leading-relaxed">
              Vetra's Verdict Engine and live analytics dashboards require wallet authentication. Connect your wallet to run contract audits.
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

      <main className="mx-auto max-w-4xl w-full px-6 py-14 flex-grow">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          Verdict Engine
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl text-ink">
          Security Auditing Panel
        </h1>

        {/* Main Scan Input Section */}
        <form
          onSubmit={handleSubmit}
          className="mt-8 flex flex-col items-stretch gap-3 rounded-3xl border border-border bg-surface p-2.5 sm:flex-row sm:items-center"
        >
          <div className="flex flex-1 items-center gap-2 rounded-full bg-bg px-4 py-2 border border-border/60">
            <Search size={16} className="shrink-0 text-muted" />
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder={type === 'contract' ? 'Contract Address (0x...)' : 'dApp URL Link (https://...)'}
              className="w-full bg-transparent font-mono text-sm text-ink outline-none placeholder:text-muted"
              required
            />
          </div>

          <div className="flex gap-2">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="rounded-full border border-border bg-bg px-4 py-2 text-xs font-semibold text-ink outline-none cursor-pointer"
            >
              <option value="contract">Contract</option>
              <option value="link">Link</option>
            </select>
          </div>

          <PillButton as="button" type="submit" variant="primary" disabled={status === 'running'} className="bg-brand text-bg font-bold whitespace-nowrap">
            {status === 'running' ? 'Auditing…' : 'Run Audit'}
          </PillButton>
        </form>

        {/* Optional source paste — no block-explorer source-fetching
            integration exists yet, so without this every scan correctly
            reports insufficient_data -> caution regardless of address. */}
        <button
          type="button"
          onClick={() => setShowSourceInput((v) => !v)}
          className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
        >
          <Code2 size={13} />
          Paste contract source (optional — no source lookup yet, so real findings need this)
          <ChevronDown size={13} className={`transition-transform ${showSourceInput ? 'rotate-180' : ''}`} />
        </button>
        <AnimatePresence>
          {showSourceInput && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <textarea
                value={sourceCode}
                onChange={(e) => setSourceCode(e.target.value)}
                placeholder="// paste Solidity source here"
                rows={8}
                className="mt-2 w-full rounded-2xl border border-border bg-surface px-4 py-3 font-mono text-xs text-ink outline-none placeholder:text-muted focus:border-brand/50"
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Threat Intelligence Flywheel Metrics */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-border bg-surface/50 px-5 py-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Exploit Signatures</p>
            <h4 className="mt-2 font-display text-2xl font-bold text-ink">138</h4>
            <p className="mt-1 text-[11px] text-muted">DeFi incident database</p>
          </div>
          <div className="rounded-2xl border border-border bg-surface/50 px-5 py-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Autonomous Growth</p>
            <h4 className="mt-2 font-display text-2xl font-bold text-[#10B981]">+8.5%</h4>
            <p className="mt-1 text-[11px] text-muted">Sandbox auto-additions</p>
          </div>
          <div className="rounded-2xl border border-border bg-surface/50 px-5 py-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Blocked Addresses</p>
            <h4 className="mt-2 font-display text-2xl font-bold text-ink">146</h4>
            <p className="mt-1 text-[11px] text-muted">Threat registry size</p>
          </div>
        </div>

        {/* Dynamic Results Staging Cards */}
        {status === 'done' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 flex items-center justify-between rounded-3xl border border-border bg-surface p-6 shadow-md"
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                Overall verdict {cacheHit && <span className="text-[10px] text-brand ml-2 uppercase font-mono tracking-normal">Cache Hit</span>}
              </p>
              <p className="mt-1 text-xs font-mono text-ink/80 select-all">{address.slice(0, 12)}…{address.slice(-4)}</p>
            </div>
            <VerdictChip verdict={verdict} size="lg" />
          </motion.div>
        )}

        <div className="mt-6 space-y-6">
          <AnimatePresence>
            {step >= 1 && (
              <Card key="static" title="Static findings">
                {staticFindings.length > 0 ? (
                  <ul className="space-y-2.5">
                    {staticFindings.map((f) => (
                      <li key={f.rule} className="flex items-center justify-between text-sm">
                        <span className="text-ink/85">{f.rule}</span>
                        <span className="flex items-center gap-3 font-mono text-xs text-muted">
                          {f.location || 'Bytecode'}
                          <span className={`uppercase font-bold ${severityColor[f.severity] || 'text-muted'}`}>{f.severity}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-muted">
                    <CheckCircle2 size={16} className="text-verdict-safe" />
                    No static issues detected.
                  </div>
                )}
              </Card>
            )}

            {step >= 2 && (
              <Card key="consensus" title="Model consensus">
                {modelConsensus.length > 0 ? (
                  <>
                    <div className="h-40">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={modelConsensus.map((m) => ({
                            ...m,
                            severity: VERDICT_ORDER.indexOf(m.risk_category) + 1,
                          }))}
                          layout="vertical"
                          margin={{ left: 8, right: 16 }}
                        >
                          <CartesianGrid horizontal={false} stroke="var(--color-border)" />
                          <XAxis type="number" domain={[0, VERDICT_ORDER.length]} hide />
                          <YAxis
                            type="category"
                            dataKey="model"
                            width={90}
                            tick={{ fill: 'var(--color-muted)', fontSize: 12 }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Bar dataKey="severity" radius={[0, 6, 6, 0]} barSize={14}>
                            {modelConsensus.map((entry) => (
                              <Cell key={entry.model} fill={VERDICTS[entry.risk_category]?.color || 'var(--color-muted)'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <ul className="mt-4 space-y-2">
                      {modelConsensus.map((m) => (
                        <li key={m.model} className="text-xs text-muted leading-relaxed">
                          <span className="font-semibold text-ink/85">{m.model}:</span> {m.rationale}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-muted">
                    <CheckCircle2 size={16} className="text-verdict-safe" />
                    Consensus reports no critical anomalies.
                  </div>
                )}
              </Card>
            )}

            {step >= 3 && (
              <Card key="exploit" title="Exploit matches">
                {exploitMatches.length > 0 ? (
                  <ul className="space-y-2.5">
                    {exploitMatches.map((m) => (
                      <li key={m.known_incident} className="flex items-center justify-between text-sm">
                        <span className="text-ink/85">{m.known_incident}</span>
                        <span className="font-mono text-xs text-muted">
                          similarity {Math.round(m.similarity_score * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-muted">
                    <CheckCircle2 size={16} className="text-verdict-safe" />
                    No matched exploit signatures in DeFi hack databases.
                  </div>
                )}
              </Card>
            )}

            {step >= 4 && (
              <Card key="attestation" title="Attestation Details">
                <div className="flex flex-col gap-2 font-mono text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
                  <span className="flex items-center gap-2">
                    <Hash size={14} />
                    {attestationTxHash ? `${attestationTxHash.slice(0, 16)}...${attestationTxHash.slice(-8)}` : 'Not attested — on-chain write failed, verdict above is still real'}
                  </span>
                  {attestationTxHash && (
                    <a
                      href={`https://testrpc.xlayer.tech/tx/${attestationTxHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-brand hover:underline font-display font-semibold uppercase tracking-wider text-[10px]"
                    >
                      View on X Layer testnet
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </Card>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Verdict Gated Sandbox Modal Popup */}
      <AnimatePresence>
        {showPopup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/30 backdrop-blur-xs"
              onClick={() => setShowPopup(false)}
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 8 }}
              className="relative z-10 w-full max-w-md rounded-3xl border-2 p-6 shadow-2xl text-ink"
              style={{
                backgroundColor: 'var(--color-bg)',
                borderColor: VERDICTS[verdict]?.color || 'var(--color-border)',
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle style={{ color: VERDICTS[verdict]?.color }} size={20} />
                  <h3 className="font-display text-base font-black uppercase tracking-tight">
                    Verdict Alert: {VERDICTS[verdict]?.label}
                  </h3>
                </div>
                <button
                  onClick={() => setShowPopup(false)}
                  className="rounded-full border border-border p-1 hover:border-ink hover:text-ink transition-all text-muted cursor-pointer"
                >
                  <Eye size={14} />
                </button>
              </div>

              <p className="mt-3 text-xs text-muted leading-relaxed">
                Vetra's Verdict engine flagged this target.
              </p>

              {/* Specific Concern Box */}
              <div
                className="mt-3 p-3.5 rounded-xl border text-xs font-semibold leading-relaxed"
                style={{
                  color: VERDICTS[verdict]?.color,
                  backgroundColor: `${VERDICTS[verdict]?.color}12`,
                  borderColor: `${VERDICTS[verdict]?.color}33`,
                }}
              >
                {modelConsensus.length > 0
                  ? modelConsensus[0].rationale
                  : staticFindings.length > 0
                  ? staticFindings[0].rule
                  : verdictConcerns[verdict]}
              </div>

              <div className="mt-5 flex flex-col gap-2">
                <button
                  onClick={handleTryInSandbox}
                  className="w-full rounded-full py-3.5 text-xs font-bold text-bg hover:opacity-90 transition-all font-display uppercase tracking-wider shadow-md shadow-brand/10"
                  style={{
                    backgroundColor: VERDICTS[verdict]?.color,
                  }}
                >
                  See what this would do to your wallet — Try in Sandbox
                </button>
                <button
                  onClick={() => setShowPopup(false)}
                  className="w-full rounded-full border border-border py-2.5 text-xs font-semibold text-muted hover:border-ink hover:text-ink transition-all cursor-pointer font-display uppercase tracking-wider"
                >
                  Dismiss Audit Alert
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>


      <Footer />
    </div>
  )
}

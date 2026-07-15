import { useEffect, useState, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, TrendingDown, ShieldCheck, Play, StopCircle, Monitor, Loader2, ShieldAlert, MousePointerClick, Lock, Compass, Sparkles } from 'lucide-react'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import PillButton from '../components/PillButton'
import DeviceFrame from '../components/DeviceFrame'
import VerdictChip from '../components/VerdictChip'
import { useCountTo } from '../lib/useCountTo'
import { useAuth } from '../context/AuthContext'
import { API_BASE_URL } from '../lib/api'

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
      className="rounded-3xl border border-border bg-surface p-6"
    >
      <h3 className="font-display text-xs font-bold tracking-tight text-ink uppercase">{title}</h3>
      <div className="mt-4">{children}</div>
    </motion.div>
  )
}

function BalanceDeltaRow({ asset, amount, usdValue }) {
  const animated = useCountTo(usdValue, { duration: 1200, delay: 200 })
  const negative = usdValue < 0
  return (
    <div className="flex items-center justify-between rounded-xl bg-surface-2 px-4 py-3 border border-border/40">
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
  const { isConnected, triggerLogin } = useAuth()
  const location = useLocation()

  // State preloading from router if coming from a dashboard audit alert
  const preloadedTarget = location.state?.target || ''
  const preloadedType = location.state?.type || 'contract'

  const [target, setTarget] = useState(preloadedTarget || '')
  const [status, setStatus] = useState('idle')
  const [step, setStep] = useState(0)

  // Sandbox environment config (decoy wallet, mock token, drainer contract) —
  // fetched from the server's own fork/deployment rather than hardcoded, since
  // hardcoded addresses go stale the moment the fork restarts or the decoy
  // wallet's key changes (this broke silently before — see auth_server.py's
  // /api/sandbox/config for why).
  const [sandboxConfig, setSandboxConfig] = useState(null)
  const [sandboxConfigError, setSandboxConfigError] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/sandbox/config`)
      .then((resp) => {
        if (!resp.ok) throw new Error('Sandbox environment not ready on the server yet.')
        return resp.json()
      })
      .then((config) => {
        setSandboxConfig(config)
        if (!preloadedTarget) setTarget(config.token_address)
      })
      .catch((err) => setSandboxConfigError(err.message))
  }, [])

  // Real static simulation state
  const [approvals, setApprovals] = useState([])
  const [balanceDeltas, setBalanceDeltas] = useState([])
  const [staticSimVerdict, setStaticSimVerdict] = useState('safe')
  const [staticSimHeadline, setStaticSimHeadline] = useState('')

  // Live Sandbox state
  const [liveUrl, setLiveUrl] = useState(preloadedType === 'link' && preloadedTarget ? preloadedTarget : 'https://uniswap.org')
  const [liveStatus, setLiveStatus] = useState('idle')
  const [liveFrame, setLiveFrame] = useState(null)
  const [liveResults, setLiveResults] = useState([])
  const [selectedResultIndex, setSelectedResultIndex] = useState(null)
  const socketRef = useRef(null)
  const canvasRef = useRef(null)

  const startLiveSession = () => {
    if (!liveUrl) return
    setLiveStatus('starting')
    setLiveFrame(null)
    setLiveResults([])
    setSelectedResultIndex(null)

    const ws = new WebSocket('ws://127.0.0.1:8765')
    socketRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'start',
        url: liveUrl
      }))
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'session_started') {
          setLiveStatus('active')
        } else if (msg.type === 'frame') {
          setLiveFrame(`data:image/jpeg;base64,${msg.data}`)
        } else if (msg.type === 'simulation_result') {
          setLiveResults((prev) => {
            const next = [...prev, msg.data]
            setSelectedResultIndex(next.length - 1)
            return next
          })
        } else if (msg.type === 'session_ended') {
          setLiveStatus('idle')
          setLiveFrame(null)
        } else if (msg.type === 'error') {
          console.error('[Live Sandbox Error]', msg.message)
          setLiveStatus('error')
        }
      } catch (e) {
        console.error(e)
      }
    }

    ws.onclose = () => {
      setLiveStatus('idle')
      setLiveFrame(null)
    }

    ws.onerror = () => {
      setLiveStatus('error')
    }
  }

  const stopLiveSession = () => {
    if (socketRef.current) {
      try {
        socketRef.current.send(JSON.stringify({ type: 'stop' }))
        socketRef.current.close()
      } catch (e) {}
    }
    setLiveStatus('idle')
    setLiveFrame(null)
  }

  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [])

  const handleMouseEvent = (e, action) => {
    if (!socketRef.current || liveStatus !== 'active') return
    const container = canvasRef.current
    if (!container) return

    const rect = container.getBoundingClientRect()
    const x = Math.round((e.clientX - rect.left) * (1280 / rect.width))
    const y = Math.round((e.clientY - rect.top) * (800 / rect.height))

    socketRef.current.send(JSON.stringify({
      type: 'mouse',
      action: action,
      x: x,
      y: y,
      button: e.button === 2 ? 'right' : 'left'
    }))
  }

  const handleKeyDown = (e) => {
    if (!socketRef.current || liveStatus !== 'active') return
    
    if (e.key.length === 1) {
      socketRef.current.send(JSON.stringify({
        type: 'keyboard',
        action: 'type',
        text: e.key
      }))
    } else {
      socketRef.current.send(JSON.stringify({
        type: 'keyboard',
        action: 'down',
        key: e.key
      }))
    }
  }

  const handleWheel = (e) => {
    if (!socketRef.current || liveStatus !== 'active') return
    e.preventDefault()
    socketRef.current.send(JSON.stringify({
      type: 'scroll',
      deltaX: Math.round(e.deltaX),
      deltaY: Math.round(e.deltaY)
    }))
  }

  const handleStaticSimulate = async (e) => {
    e.preventDefault()

    if (!sandboxConfig) {
      alert(sandboxConfigError || 'Sandbox environment still loading — try again in a moment.')
      return
    }

    setStatus('running')
    setStep(0)

    try {
      const token = localStorage.getItem('vetra_session_token')

      const t1 = setTimeout(() => setStep(1), 800)
      const t2 = setTimeout(() => setStep(2), 1600)

      const isCalldata = target.trim().startsWith('0x') && target.trim().length > 42

      const payload = {
        chain: 'evm',
        decoy_wallet: sandboxConfig.decoy_wallet,
        target: isCalldata ? sandboxConfig.token_address : target.trim(),
        tracked_tokens: [sandboxConfig.token_address],
      }

      if (isCalldata) {
        payload.calldata = target.trim()
      } else {
        payload.function_signature = 'approve(address,uint256)'
        payload.args = [
          sandboxConfig.drainer_address,
          '115792089237316195423570985008687907853269984665640564039457584007913129639935'
        ]
      }

      const resp = await fetch(`${API_BASE_URL}/api/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!resp.ok) {
        throw new Error(await resp.text())
      }

      const data = await resp.json()

      clearTimeout(t1)
      clearTimeout(t2)

      setApprovals(data.approvals || [])
      setBalanceDeltas(data.balance_deltas || [])
      setStaticSimVerdict(data.risk_summary?.verdict || 'safe')
      setStaticSimHeadline(data.risk_summary?.headline || 'No vulnerabilities detected during isolated dry-run execution.')

      setStep(3)
      setStatus('done')
    } catch (err) {
      console.error('Static simulation run failure:', err)
      alert(err.message || 'Failed to complete transaction simulation.')
      setStatus('idle')
      setStep(0)
    }
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
              <Monitor size={24} />
            </div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">Access Gated</h2>
            <p className="mt-3 text-sm text-muted leading-relaxed">
              Vetra's Simulation Sandbox panel requires wallet authentication. Connect your wallet to access interactive sandboxing.
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
        {/* Breadcrumb if redirected from audit verdict popup */}
        {location.state?.target && (
          <div className="mb-4 inline-flex items-center gap-2 text-xs font-semibold text-muted bg-surface px-4 py-2 rounded-full border border-border">
            <span className="w-2 h-2 rounded-full bg-brand" />
            Continuing from audit of {location.state.target.slice(0, 12)}…{location.state.target.slice(-4)}
          </div>
        )}

        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          Isolated Environment
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl text-ink">
          Simulation Sandbox
        </h1>

        <div className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-[#3b99fc]/20 bg-[#3b99fc]/5 px-4 py-2.5 text-xs font-medium text-[#3b99fc]">
          <FlaskConical size={14} />
          Simulated decoy workspace — no real gas fees or assets are ever spent.
        </div>

        {/* Input Target */}
        <form
          onSubmit={handleStaticSimulate}
          className="mt-8 flex flex-col items-stretch gap-3 rounded-3xl border border-border bg-surface p-2.5 sm:flex-row sm:items-center"
        >
          <div className="flex flex-1 items-center gap-2 rounded-full bg-bg px-4 py-2 border border-border/60">
            <Compass size={16} className="text-muted shrink-0" />
            <input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Contract address + method, or transaction calldata payload"
              className="w-full bg-transparent font-mono text-sm text-ink outline-none placeholder:text-muted"
              required
            />
          </div>
          <PillButton
            as="button"
            type="submit"
            variant="primary"
            disabled={status === 'running' || (!sandboxConfig && !sandboxConfigError)}
            className="bg-brand text-bg font-bold whitespace-nowrap"
          >
            {status === 'running'
              ? 'Simulating…'
              : !sandboxConfig && !sandboxConfigError
                ? 'Loading sandbox…'
                : 'Simulate Tx'}
          </PillButton>
        </form>
        {sandboxConfigError && (
          <p className="mt-2 text-xs text-verdict-critical">{sandboxConfigError}</p>
        )}

        <div className="mt-8">
          <DeviceFrame>
            <div className="bg-bg p-6">
              {/* Simulated Sandbox Wallet details (neutral gray/blue, explicitly separate) */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/40 pb-4 mb-6">
                <div className="flex items-center gap-2.5">
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-500/10 border border-slate-500/20 px-2.5 py-1 text-xs font-bold text-slate-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                    Sandbox Wallet (Simulated)
                  </span>
                  <span className="font-mono text-xs text-muted">{sandboxConfig?.decoy_wallet || 'loading...'}</span>
                </div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-slate-500 border border-slate-500/30 bg-slate-500/10 px-2 py-0.5 rounded-md">
                  SIMULATED
                </span>
              </div>

              <div className="space-y-6">
                <AnimatePresence>
                  {step >= 1 && (
                    <Card key="approvals" title="Approvals Staged">
                      {approvals.length > 0 ? (
                        <ul className="space-y-2.5">
                          {approvals.map((a, aIdx) => (
                            <li key={aIdx} className="flex items-center justify-between text-sm">
                              <span className="font-mono text-ink/80 truncate max-w-[200px]">{a.spender}</span>
                              <span className="flex items-center gap-2 font-mono text-xs">
                                <span className="text-muted">{a.asset}</span>
                                <span className={a.unlimited ? 'text-verdict-critical font-bold' : 'text-verdict-safe'}>
                                  {a.amount}
                                </span>
                                {a.known_drainer && (
                                  <span className="rounded-full bg-verdict-critical/10 px-2.5 py-0.5 text-verdict-critical font-semibold border border-verdict-critical/20">
                                    known drainer
                                  </span>
                                )}
                              </span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <div className="flex items-center gap-2 text-sm text-muted">
                          <ShieldCheck size={16} className="text-verdict-safe" />
                          No contract authorization changes staged.
                        </div>
                      )}
                    </Card>
                  )}

                  {step >= 2 && (
                    <Card key="balances" title="Balance changes">
                      {balanceDeltas.length > 0 ? (
                        <div className="space-y-2.5">
                          {balanceDeltas.map((b, bIdx) => (
                            <BalanceDeltaRow
                              key={bIdx}
                              asset={b.asset}
                              amount={b.amount}
                              usdValue={b.usd_value}
                            />
                          ))}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-sm text-muted">
                          <ShieldCheck size={16} className="text-verdict-safe" />
                          No token balance shifts predicted.
                        </div>
                      )}
                    </Card>
                  )}

                  {step >= 3 && (
                    <Card key="risk" title="Simulation Verdict">
                      <div className="flex items-center justify-between gap-3">
                        <p className="max-w-sm text-xs text-muted leading-relaxed">
                          {staticSimHeadline}
                        </p>
                        <VerdictChip verdict={staticSimVerdict} size="lg" />
                      </div>
                    </Card>
                  )}
                </AnimatePresence>


                {status !== 'done' && step === 0 && (
                  <div className="flex items-center gap-2 py-6 text-sm text-muted">
                    <ShieldCheck size={16} className="text-slate-400" />
                    Launch transaction simulation to compute balance changes and approval warnings.
                  </div>
                )}
              </div>
            </div>
          </DeviceFrame>
        </div>

        {/* Live Container Session Section */}
        <div className="mt-16 border-t border-border pt-12">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            Interactive Container
          </p>
          <h2 className="mt-3 font-display text-2xl font-black tracking-tight text-ink">
            Interactive Live Sandbox
          </h2>
          <p className="mt-2 text-sm text-muted max-w-2xl leading-relaxed">
            Launch a sandbox browser inside an isolated backend container to safely click through target sites. Vetra intercepts contract interaction requests automatically.
          </p>

          <div className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-verdict-caution/20 bg-verdict-caution/5 px-4 py-2.5 text-xs font-medium text-verdict-caution">
            <Lock size={14} />
            Isolated container routing and user agent proxying active.
          </div>

          {/* Controls */}
          {liveStatus === 'idle' || liveStatus === 'error' ? (
            <div className="mt-6 flex flex-col gap-3 rounded-3xl border border-border bg-surface p-2.5 sm:flex-row sm:items-center">
              <div className="flex flex-1 items-center gap-2 rounded-full bg-bg px-4 py-2 border border-border/60">
                <Monitor size={16} className="text-muted shrink-0" />
                <input
                  value={liveUrl}
                  onChange={(e) => setLiveUrl(e.target.value)}
                  placeholder="Enter target dApp URL (e.g. https://uniswap.org)"
                  className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-muted"
                />
              </div>
              <PillButton as="button" onClick={startLiveSession} variant="primary" className="bg-brand text-bg font-bold whitespace-nowrap">
                Launch Live Session
              </PillButton>
            </div>
          ) : (
            <div className="mt-6 flex items-center justify-between rounded-2xl border border-border bg-surface px-5 py-4 shadow-sm">
              <div className="flex items-center gap-3">
                {liveStatus === 'starting' ? (
                  <Loader2 size={16} className="animate-spin text-verdict-caution" />
                ) : (
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-verdict-safe opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-verdict-safe"></span>
                  </span>
                )}
                <span className="font-mono text-sm text-ink font-semibold">
                  {liveStatus === 'starting' ? 'Spawning isolated container...' : `Streaming Live: ${liveUrl}`}
                </span>
              </div>
              <PillButton as="button" onClick={stopLiveSession} className="!bg-verdict-critical !text-bg hover:opacity-90 font-bold">
                <StopCircle size={14} className="mr-1.5 inline" />
                End Session
              </PillButton>
            </div>
          )}

          {liveStatus === 'error' && (
            <div className="mt-4 rounded-2xl border border-verdict-critical/20 bg-verdict-critical/5 p-4 text-xs font-semibold text-verdict-critical leading-relaxed">
              Could not establish connection to the local sandbox streaming node (ws://127.0.0.1:8765). Make sure the backend server is running.
            </div>
          )}

          {/* Session Viewport & Staged Reports */}
          {(liveStatus === 'active' || liveStatus === 'starting') && (
            <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-12">
              {/* Screen Viewer */}
              <div className="lg:col-span-8">
                <div className="relative overflow-hidden rounded-2xl border border-border bg-black shadow-2xl">
                  {/* Browser top-bar */}
                  <div className="flex items-center gap-2 border-b border-border bg-surface px-4 py-2.5">
                    <div className="flex gap-1.5">
                      <span className="h-3 w-3 rounded-full bg-[#ef4444]"></span>
                      <span className="h-3 w-3 rounded-full bg-[#eab308]"></span>
                      <span className="h-3 w-3 rounded-full bg-[#22c55e]"></span>
                    </div>
                    <div className="mx-auto max-w-md flex-1 rounded-md bg-bg px-3 py-1 text-center font-mono text-xs text-muted truncate border border-border/40">
                      {liveUrl}
                    </div>
                  </div>

                  {/* Screencast Screen */}
                  <div 
                    className="relative aspect-[16/10] w-full cursor-crosshair bg-neutral-950 focus:outline-none"
                    tabIndex={0}
                    onKeyDown={handleKeyDown}
                    onWheel={handleWheel}
                    ref={canvasRef}
                    onMouseDown={(e) => handleMouseEvent(e, 'down')}
                    onMouseUp={(e) => handleMouseEvent(e, 'up')}
                    onMouseMove={(e) => handleMouseEvent(e, 'move')}
                  >
                    {liveFrame ? (
                      <img 
                        src={liveFrame} 
                        alt="Browser Stream"
                        className="h-full w-full object-contain pointer-events-none"
                        draggable={false}
                      />
                    ) : (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-muted bg-neutral-950">
                        <Loader2 className="h-8 w-8 animate-spin text-brand" />
                        <span className="text-sm font-semibold uppercase tracking-wider text-muted">Waiting for video stream...</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Intercepted Wallet Interactions & Report */}
              <div className="lg:col-span-4 space-y-6">
                <div className="rounded-2xl border border-border bg-surface p-6">
                  <h3 className="font-display text-sm font-bold tracking-tight text-ink uppercase">
                    Intercepted Actions
                  </h3>
                  <p className="mt-1 text-xs text-muted">
                    Signatures and transactions captured during this session.
                  </p>

                  {liveResults.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed border-border p-8 text-center text-xs text-muted">
                      <MousePointerClick className="mx-auto h-6 w-6 text-muted mb-2" />
                      No requests intercepted yet. Trigger a wallet sign request inside the screen window.
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      {liveResults.map((res, idx) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedResultIndex(idx)}
                          className={`w-full text-left rounded-xl border p-3.5 transition-all flex items-center justify-between cursor-pointer ${
                            selectedResultIndex === idx
                              ? 'border-brand bg-surface-2 shadow-sm'
                              : 'border-border bg-bg/50 hover:bg-surface-2'
                          }`}
                        >
                          <div className="space-y-1">
                            <span className="font-mono text-[10px] font-bold uppercase text-muted">
                              {res.chain} · {res.method}
                            </span>
                            <p className="text-xs text-ink truncate max-w-[150px]">
                              To: {res.simulation?.target?.address || 'N/A'}
                            </p>
                          </div>
                          {res.simulation?.risk_summary?.verdict ? (
                            <VerdictChip verdict={res.simulation.risk_summary.verdict} size="sm" />
                          ) : (
                            <span className="text-[10px] bg-slate-500/10 border border-slate-500/20 px-2 py-0.5 rounded-md font-bold text-slate-500 uppercase tracking-wide">
                              Signed
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Display Report for selected result */}
                {selectedResultIndex !== null && liveResults[selectedResultIndex] && (
                  <AnimatePresence mode="wait">
                    {(() => {
                      const res = liveResults[selectedResultIndex];
                      const sim = res.simulation;
                      if (!sim) return null;

                      return (
                        <motion.div
                          key={selectedResultIndex}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 10 }}
                          className="space-y-4"
                        >
                          {sim.risk_summary && (
                            <Card title="Risk Verdict">
                              <div className="flex items-center justify-between gap-3">
                                <p className="text-xs text-muted max-w-[160px]">
                                  {sim.risk_summary.headline}
                                </p>
                                <VerdictChip verdict={sim.risk_summary.verdict} size="md" />
                              </div>
                            </Card>
                          )}

                          {sim.balance_deltas && sim.balance_deltas.length > 0 && (
                            <Card title="Simulated Balance Changes">
                              <div className="space-y-2">
                                {sim.balance_deltas.map((b, bIdx) => (
                                  <BalanceDeltaRow
                                    key={bIdx}
                                    asset={b.asset}
                                    amount={b.amount}
                                    usdValue={b.usd_value}
                                  />
                                ))}
                              </div>
                            </Card>
                          )}

                          {sim.approvals && sim.approvals.length > 0 && (
                            <Card title="Approvals Staged">
                              <ul className="space-y-2">
                                {sim.approvals.map((a, aIdx) => (
                                  <li key={aIdx} className="flex items-center justify-between text-xs">
                                    <span className="font-mono text-ink/80 truncate max-w-[120px]">{a.spender}</span>
                                    <span className="flex items-center gap-1.5 font-mono">
                                      <span className="text-muted">{a.asset}</span>
                                      <span className={a.unlimited ? 'text-verdict-critical font-bold' : 'text-verdict-safe'}>
                                        {a.amount}
                                      </span>
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </Card>
                          )}
                        </motion.div>
                      );
                    })()}
                  </AnimatePresence>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}

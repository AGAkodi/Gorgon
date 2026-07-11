import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, TrendingDown, ShieldCheck, Play, StopCircle, Monitor, Loader2, ShieldAlert, MousePointerClick, Lock } from 'lucide-react'
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

  // Live Sandbox state
  const [liveUrl, setLiveUrl] = useState('https://uniswap.org')
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
    // Scale client coords to 1280x800 browser context coords
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
    
    // Dispatch regular characters as "type", control/navigation keys as "down"
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

        <div className="mt-16 border-t border-border pt-12">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verdict-safe">
            Layer 2 Capability
          </p>
          <h2 className="mt-3 font-display text-2xl font-bold tracking-tight">
            Interactive Live Sandbox
          </h2>
          <p className="mt-2 text-sm text-muted">
            Launch a live, containerized browser session to interact with external sites.
            Vetra intercepts signature and transaction requests, simulating them against the fork
            to generate an impact report in real-time.
          </p>

          <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-verdict-caution/30 bg-verdict-caution/10 px-4 py-2 text-xs font-medium text-verdict-caution">
            <Lock size={14} />
            In Hardening Mode — isolated container and anti-fingerprint routing active. Not for production use.
          </div>

          {/* Controls */}
          {liveStatus === 'idle' || liveStatus === 'error' ? (
            <div className="mt-6 flex flex-col gap-3 rounded-full border border-border bg-surface p-2 sm:flex-row sm:items-center">
              <div className="flex flex-1 items-center gap-2 rounded-full px-4 py-2">
                <Monitor size={16} className="text-muted" />
                <input
                  value={liveUrl}
                  onChange={(e) => setLiveUrl(e.target.value)}
                  placeholder="Enter target URL (e.g. https://uniswap.org)"
                  className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-muted"
                />
              </div>
              <PillButton as="button" onClick={startLiveSession} variant="primary">
                Launch Session
              </PillButton>
            </div>
          ) : (
            <div className="mt-6 flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3">
              <div className="flex items-center gap-3">
                {liveStatus === 'starting' ? (
                  <Loader2 size={16} className="animate-spin text-verdict-caution" />
                ) : (
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-verdict-safe opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-verdict-safe"></span>
                  </span>
                )}
                <span className="font-mono text-sm text-ink">
                  {liveStatus === 'starting' ? 'Spawning isolated container...' : `Streaming: ${liveUrl}`}
                </span>
              </div>
              <PillButton as="button" onClick={stopLiveSession} className="!bg-verdict-critical !text-white hover:!bg-red-600">
                <StopCircle size={14} className="mr-1.5 inline" />
                End Session
              </PillButton>
            </div>
          )}

          {liveStatus === 'error' && (
            <div className="mt-3 rounded-lg bg-verdict-critical/10 p-3 text-sm text-verdict-critical">
              Failed to establish WebSocket connection to the sandbox streaming server (ws://127.0.0.1:8765). Ensure the server is running.
            </div>
          )}

          {/* Session Viewport & Reports */}
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
                    <div className="mx-auto max-w-md flex-1 rounded-md bg-bg px-3 py-1 text-center font-mono text-xs text-muted truncate">
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
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-muted">
                        <Loader2 className="h-8 w-8 animate-spin text-muted" />
                        <span className="text-sm font-medium">Waiting for video stream...</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Intercepted Wallet Interactions & Report */}
              <div className="lg:col-span-4 space-y-6">
                <div className="rounded-2xl border border-border bg-surface p-6">
                  <h3 className="font-display text-base font-bold tracking-tight">
                    Intercepted Actions
                  </h3>
                  <p className="mt-1 text-xs text-muted">
                    Signatures and transactions captured during this session.
                  </p>

                  {liveResults.length === 0 ? (
                    <div className="mt-6 rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted">
                      <MousePointerClick className="mx-auto h-8 w-8 text-muted/50 mb-3" />
                      No requests intercepted yet. Click around the site to initiate wallet calls.
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      {liveResults.map((res, idx) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedResultIndex(idx)}
                          className={`w-full text-left rounded-xl border p-3.5 transition-all flex items-center justify-between ${
                            selectedResultIndex === idx
                              ? 'border-ink/20 bg-surface-2'
                              : 'border-border bg-surface-2/40 hover:bg-surface-2/70'
                          }`}
                        >
                          <div className="space-y-1">
                            <span className="font-mono text-xs font-semibold uppercase text-muted">
                              {res.chain} · {res.method}
                            </span>
                            <p className="text-xs text-ink truncate max-w-[180px]">
                              To: {res.simulation?.target?.address || 'N/A'}
                            </p>
                          </div>
                          {res.simulation?.risk_summary?.verdict ? (
                            <VerdictChip verdict={res.simulation.risk_summary.verdict} size="sm" />
                          ) : (
                            <span className="text-[10px] bg-border px-2.5 py-0.5 rounded-full text-muted uppercase">
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
                                <p className="text-xs text-muted max-w-[180px]">
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
                                      <span className={a.unlimited ? 'text-verdict-critical' : 'text-verdict-safe'}>
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

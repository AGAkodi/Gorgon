import { motion } from 'framer-motion'
import { ArrowRight, Sparkles, Monitor, ShieldCheck, Flame, ShieldAlert, Cpu } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import PillButton from '../components/PillButton'
import DeviceFrame from '../components/DeviceFrame'
import VerdictChip from '../components/VerdictChip'
import { useCountTo } from '../lib/useCountTo'

const floatFade = {
  hidden: { opacity: 0, y: 14 },
  show: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay, ease: 'easeOut' },
  }),
}

function VerdictMock() {
  return (
    <div className="bg-bg p-6 pb-14 font-mono text-xs text-muted border-b border-border/40">
      <div className="flex items-center justify-between border-b border-border/40 pb-3 mb-4">
        <span className="text-ink font-bold select-all">0x7a3f...19Ec</span>
        <span className="text-verdict-safe font-semibold">confidence 94%</span>
      </div>
      <div className="space-y-3">
        {[
          ['Static scan', '92%', 'var(--color-verdict-safe)'],
          ['AI Consensus', '80%', 'var(--color-verdict-safe)'],
          ['Exploit match', '34%', 'var(--color-verdict-caution)'],
          ['Sealed hash', '100%', 'var(--color-ink)'],
        ].map(([label, percentage, color]) => (
          <div key={label} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-ink/75 font-semibold">{label}</span>
            <div className="h-2 flex-1 rounded-full bg-surface-2 overflow-hidden">
              <div className="h-full rounded-full" style={{ width: percentage, backgroundColor: color }} />
            </div>
            <span className="w-8 text-right font-bold text-ink/90">{percentage}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function SandboxMock() {
  const delta = useCountTo(-2.48, { duration: 1300, delay: 500 })
  return (
    <div className="bg-bg p-6 pb-14 font-mono text-xs text-muted">
      <div className="flex items-center justify-between border-b border-border/40 pb-3 mb-4">
        <span className="text-ink font-bold flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          Sandbox (Simulated)
        </span>
        <span className="text-[10px] font-bold tracking-wider uppercase text-blue-500 border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 rounded-md">
          SIMULATED
        </span>
      </div>
      <div className="space-y-2.5">
        <div className="flex items-center justify-between rounded-xl bg-surface-2 px-4 py-2.5 border border-border/40">
          <span className="text-ink/75 font-medium">Impersonated Account</span>
          <span className="text-ink/90 font-semibold select-all">0x0d3c...0001</span>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-surface-2 px-4 py-2.5 border border-border/40">
          <span className="text-ink/75 font-medium">Calculated Balance Delta</span>
          <span className="text-verdict-critical font-bold">{delta.toFixed(2)} ETH</span>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-surface-2 px-4 py-2.5 border border-border/40">
          <span className="text-ink/75 font-medium">Token Approvals</span>
          <span className="text-verdict-critical font-semibold">Unlimited USDC (Drainer)</span>
        </div>
      </div>
    </div>
  )
}

export default function Hero() {
  const { triggerLogin } = useAuth()

  return (
    <section className="relative overflow-hidden pt-12 pb-20 border-b border-border">
      {/* Decorative page layout lines */}
      <div className="absolute top-1/3 left-0 w-32 h-96 border-r border-t border-border/40 rounded-r-[60px] pointer-events-none" />
      <div className="absolute top-1/2 right-0 w-44 h-96 border-l border-b border-border/40 rounded-l-[60px] pointer-events-none" />

      <div className="mx-auto max-w-7xl px-6">
        {/* Main Hero Header */}
        <div className="text-center max-w-3xl mx-auto flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="inline-flex items-center gap-1.5 rounded-full border border-brand/20 bg-brand/5 px-4 py-1.5 text-xs font-semibold tracking-wide text-brand mb-6"
          >
            <Sparkles size={12} />
            Next-Gen Security Guard for Web3 Agents
          </motion.div>

          <motion.h1
            initial="hidden"
            animate="show"
            variants={floatFade}
            className="font-display text-4xl font-extrabold tracking-tight text-ink sm:text-6xl"
          >
            A security verdict before any agent signs a thing.
          </motion.h1>

          <motion.p
            custom={0.1}
            initial="hidden"
            animate="show"
            variants={floatFade}
            className="mt-6 text-base sm:text-lg leading-relaxed text-muted max-w-2xl"
          >
            Protect your assets with instantaneous multi-model AI consensus auditing, secure on-chain attestations, and user-driven sandbox simulations.
          </motion.p>

          <motion.div
            custom={0.2}
            initial="hidden"
            animate="show"
            variants={floatFade}
            className="mt-8 flex items-center justify-center gap-4"
          >
            <PillButton as="button" onClick={triggerLogin} variant="primary" className="bg-brand text-bg font-bold">
              Get Started
            </PillButton>
            <PillButton
              as="button"
              onClick={() => {
                const el = document.querySelector('#developers')
                if (el) el.scrollIntoView({ behavior: 'smooth' })
              }}
              variant="secondary"
            >
              View Docs
            </PillButton>
          </motion.div>
        </div>

        {/* Sana-Style Split Pillars Section */}
        <div className="mt-20 grid gap-12 lg:grid-cols-2 lg:gap-16 border-t border-border pt-16">
          {/* Left Pillar: Verdict Engine */}
          <div className="flex flex-col justify-between">
            <div className="mb-8">
              <div className="w-10 h-10 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand mb-4">
                <Cpu size={20} />
              </div>
              <h3 className="font-display text-2xl font-bold tracking-tight text-ink">
                Verdict Engine Pillar
              </h3>
              <p className="mt-3 text-sm text-muted leading-relaxed max-w-md">
                Analyzes contract risk using native compilers, Slither, and Anchor static findings coupled with deep LLM multi-model verification. Generates a signed, verifiable attestation.
              </p>
            </div>

            <div className="relative mt-4">
              <DeviceFrame>
                <VerdictMock />
              </DeviceFrame>
              {/* Floating Chips */}
              <div className="absolute top-2 right-6">
                <VerdictChip verdict="safe" size="sm" className="shadow-lg border border-border" />
              </div>
              <div className="absolute bottom-3 left-6">
                <VerdictChip verdict="caution" size="sm" className="shadow-lg border border-border" />
              </div>
            </div>
          </div>

          {/* Right Pillar: Simulation Sandbox */}
          <div className="flex flex-col justify-between">
            <div className="mb-8">
              <div className="w-10 h-10 rounded-2xl bg-[#3b99fc]/10 border border-[#3b99fc]/20 flex items-center justify-center text-[#3b99fc] mb-4">
                <Monitor size={20} />
              </div>
              <h3 className="font-display text-2xl font-bold tracking-tight text-ink">
                Simulation Sandbox Pillar
              </h3>
              <p className="mt-3 text-sm text-muted leading-relaxed max-w-md">
                Spawns a custom iframe browser routing transaction requests into a local EVM sandbox. Evaluates balance changes, approved spenders, and ownership state before real executions.
              </p>
            </div>

            <div className="relative mt-4">
              <DeviceFrame>
                <SandboxMock />
              </DeviceFrame>
              {/* Floating Chips */}
              <div className="absolute top-2 right-6 inline-flex items-center rounded-full border font-medium bg-verdict-critical/10 border-verdict-critical/30 text-verdict-critical text-xs px-2.5 py-1 gap-1 shadow-lg border border-border">
                <Flame size={14} strokeWidth={2.25} />
                Critical Drainer
              </div>
              <div className="absolute bottom-3 left-6 inline-flex items-center rounded-full border font-medium bg-blue-500/10 border-blue-500/30 text-blue-500 text-xs px-2.5 py-1 gap-1 shadow-lg border border-border">
                <ShieldAlert size={14} strokeWidth={2.25} />
                Decoy Session
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

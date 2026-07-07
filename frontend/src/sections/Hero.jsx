import { motion } from 'framer-motion'
import { ArrowRight, TrendingDown } from 'lucide-react'
import PillButton from '../components/PillButton'
import DeviceFrame from '../components/DeviceFrame'
import Ribbon from '../components/Ribbon'
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

function DashboardMock() {
  return (
    <div className="bg-bg p-5 font-mono text-xs text-muted">
      <div className="flex items-center justify-between">
        <span>0x7a3f...19Ec</span>
        <span className="text-verdict-safe">confidence 0.94</span>
      </div>
      <div className="mt-4 space-y-2">
        {[
          ['Static analysis', 'w-11/12'],
          ['Model consensus', 'w-4/5'],
          ['Exploit match', 'w-2/3'],
          ['Attestation', 'w-full'],
        ].map(([label, width]) => (
          <div key={label} className="flex items-center gap-3">
            <span className="w-32 shrink-0 text-ink/70">{label}</span>
            <div className="h-1.5 flex-1 rounded-full bg-surface-2">
              <div className={`h-1.5 ${width} rounded-full bg-ink/40`} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function SandboxMock() {
  const delta = useCountTo(-2.48, { duration: 1300, delay: 500 })
  return (
    <div className="bg-bg p-5 font-mono text-xs text-muted">
      <div className="flex items-center justify-between">
        <span>decoy wallet · isolated</span>
        <span className="text-verdict-critical">unlimited approval</span>
      </div>
      <div className="mt-4 space-y-2.5">
        <div className="flex items-center justify-between rounded-lg bg-surface-2 px-3 py-2">
          <span className="text-ink/70">ETH balance</span>
          <span className="text-verdict-critical">{delta.toFixed(2)} ETH</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-surface-2 px-3 py-2">
          <span className="text-ink/70">Spender approval</span>
          <span className="text-ink/70">0x00...drain</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-surface-2 px-3 py-2">
          <span className="text-ink/70">Ownership</span>
          <span className="text-ink/70">unchanged</span>
        </div>
      </div>
    </div>
  )
}

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-6 pt-14 sm:pt-20">
        <div className="grid gap-14 lg:grid-cols-2 lg:divide-x lg:divide-border">
          <motion.div
            className="lg:pr-12"
            initial="hidden"
            animate="show"
            variants={floatFade}
          >
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verdict-safe">
              Verify
            </p>
            <h1 className="mt-4 font-display text-4xl font-extrabold tracking-tight sm:text-5xl">
              A security verdict before any agent signs a thing.
            </h1>
            <p className="mt-4 max-w-md text-base leading-relaxed text-muted">
              Multi-model AI consensus, static analysis, and exploit intelligence
              matching, sealed with an on-chain attestation any agent can query.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <PillButton to="/#developers" variant="primary">
                View Docs
              </PillButton>
              <PillButton to="/dashboard" variant="secondary">
                Live Demo
                <ArrowRight size={16} />
              </PillButton>
            </div>
          </motion.div>

          <motion.div
            className="lg:pl-12"
            initial="hidden"
            animate="show"
            custom={0.12}
            variants={floatFade}
          >
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verdict-critical">
              Simulate
            </p>
            <h1 className="mt-4 font-display text-4xl font-extrabold tracking-tight sm:text-5xl">
              See the wallet impact before you feel it.
            </h1>
            <p className="mt-4 max-w-md text-base leading-relaxed text-muted">
              Transaction simulation shows exact balance changes, approvals, and
              ownership transfers, run against an isolated decoy wallet.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <PillButton to="/sandbox" variant="primary">
                Try Sandbox
              </PillButton>
              <PillButton to="/sandbox" variant="secondary">
                See Example
                <TrendingDown size={16} />
              </PillButton>
            </div>
          </motion.div>
        </div>
      </div>

      <Ribbon className="mt-10 sm:mt-16" />

      <div className="relative z-10 mx-auto -mt-10 max-w-7xl px-6 pb-24 sm:-mt-16">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-10">
          <motion.div
            className="relative"
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.3 }}
            variants={floatFade}
          >
            <DeviceFrame>
              <DashboardMock />
            </DeviceFrame>
            <div className="absolute -right-3 -top-4 sm:-right-5">
              <VerdictChip verdict="safe" size="sm" className="shadow-lg shadow-black/40" />
            </div>
            <div className="absolute -bottom-4 left-6">
              <VerdictChip verdict="caution" size="sm" className="shadow-lg shadow-black/40" />
            </div>
          </motion.div>

          <motion.div
            className="relative"
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.3 }}
            custom={0.12}
            variants={floatFade}
          >
            <DeviceFrame>
              <SandboxMock />
            </DeviceFrame>
            <div className="absolute -right-3 -top-4 flex items-center gap-1.5 rounded-full border border-verdict-critical/30 bg-verdict-critical/10 px-3 py-1.5 text-xs font-medium text-verdict-critical shadow-lg shadow-black/40 sm:-right-5">
              <TrendingDown size={14} />
              -2.48 ETH
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

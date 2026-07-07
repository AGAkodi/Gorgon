import { motion } from 'framer-motion'
import { ScanSearch, Brain, Fingerprint, Stamp } from 'lucide-react'

const STEPS = [
  {
    icon: ScanSearch,
    title: 'Static analysis',
    body: 'Slither and Anchor-aware analyzers surface reentrancy, access-control, and unchecked-call findings.',
  },
  {
    icon: Brain,
    title: 'Multi-model consensus',
    body: '2-3 models independently assess risk. Agreement raises confidence; disagreement is surfaced, not hidden.',
  },
  {
    icon: Fingerprint,
    title: 'Exploit match',
    body: 'Findings are matched against a corpus of known incidents and SWC entries for similarity.',
  },
  {
    icon: Stamp,
    title: 'Attestation',
    body: 'The verdict hash is written on-chain so any agent can verify it later without re-running analysis.',
  },
]

const item = {
  hidden: { opacity: 0, y: 16 },
  show: (i) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, delay: i * 0.12, ease: 'easeOut' },
  }),
}

export default function HowItWorks() {
  return (
    <section className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Pipeline
        </p>
        <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          How it works
        </h2>

        <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
          {STEPS.map((step, i) => {
            const Icon = step.icon
            return (
              <motion.div
                key={step.title}
                custom={i}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, amount: 0.4 }}
                variants={item}
                className="relative rounded-2xl border border-border bg-surface p-6"
              >
                <span className="text-xs font-mono text-muted">0{i + 1}</span>
                <Icon size={22} strokeWidth={1.75} className="mt-3" />
                <h3 className="mt-4 font-display text-lg font-bold tracking-tight">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

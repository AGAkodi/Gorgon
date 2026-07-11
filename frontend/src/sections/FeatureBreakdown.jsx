import { motion } from 'framer-motion'
import { Search, Globe, Code, ShieldCheck, Terminal, Compass } from 'lucide-react'

const FEATURES = [
  {
    icon: Search,
    title: 'Smart Contract Auditing',
    desc: 'Audit EVM/Solana contracts instantly. Runs Slither, Anchor tools, compiler verification, and multi-model consensus checks.',
    tag: null,
  },
  {
    icon: Globe,
    title: 'Web Link Verification',
    desc: 'Input landing pages or dApp domains. Scrapes the frontend and detects malicious wallet drainage code scripts before interaction.',
    tag: null,
  },
  {
    icon: ShieldCheck,
    title: 'On-Chain Attestations',
    desc: 'Verdicts are cryptographically hashed and published to X Layer testnet, serving as a permanent security log queryable by AI agents.',
    tag: null,
  },
  {
    icon: Compass,
    title: 'Simulation Sandbox',
    desc: 'Streams a live, user-driven session in an isolated container. Intercepts all signature actions and calculates asset balance deltas.',
    tag: null,
  },
  {
    icon: Code,
    title: 'Full Repository Scanning',
    desc: 'Deep integration into GitHub repositories to audit full source code and verify build compilation pipeline reproducibility.',
    tag: 'Coming Soon',
  },
]

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  show: (i) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay: i * 0.08, ease: 'easeOut' },
  }),
}

export default function FeatureBreakdown() {
  return (
    <section id="features" className="border-t border-border bg-surface/30">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            Capabilities
          </p>
          <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
            Vetra Core Security Modules
          </h2>
          <p className="mt-4 text-sm text-muted">
            Auditing APIs and sandbox environments built specifically for Web3 agent actions and interactive wallet approvals.
          </p>
        </div>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feat, i) => {
            const Icon = feat.icon
            return (
              <motion.div
                key={feat.title}
                custom={i}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, amount: 0.2 }}
                variants={cardVariants}
                className="relative rounded-3xl border border-border bg-surface p-6 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="w-9 h-9 rounded-xl border border-border bg-bg flex items-center justify-center text-brand">
                      <Icon size={16} />
                    </div>
                    {feat.tag && (
                      <span className="text-[10px] font-bold tracking-wider uppercase text-brand border border-brand/30 bg-brand/10 px-2 py-0.5 rounded-full">
                        {feat.tag}
                      </span>
                    )}
                  </div>
                  <h3 className="mt-4 font-display text-base font-bold text-ink">
                    {feat.title}
                  </h3>
                  <p className="mt-2 text-xs text-muted leading-relaxed">
                    {feat.desc}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

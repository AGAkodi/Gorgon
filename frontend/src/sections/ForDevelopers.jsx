import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import PillButton from '../components/PillButton'

const SNIPPET = `{
  "tool": "get_security_verdict",
  "input": {
    "chain": "evm",
    "address": "0x7a3f...19Ec"
  }
}

// → { "verdict": "safe", "confidence": 0.94, ... }`

export default function ForDevelopers() {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(SNIPPET)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // clipboard access denied — no-op, button stays interactive
    }
  }

  return (
    <section id="developers" className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center lg:gap-16">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              For developers
            </p>
            <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              Two tools. Any agent. One MCP call.
            </h2>
            <p className="mt-4 max-w-md text-base leading-relaxed text-muted">
              <code className="font-mono text-sm text-ink/80">get_security_verdict</code> and{' '}
              <code className="font-mono text-sm text-ink/80">simulate_wallet_interaction</code>{' '}
              are exposed over MCP with pay-per-call billing, no negotiation required.
            </p>
            <div className="mt-8">
              <PillButton href="#developers" variant="primary">
                Read the MCP reference
              </PillButton>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <span className="font-mono text-xs text-muted">mcp · get_security_verdict</span>
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-muted transition-colors hover:text-ink"
              >
                {copied ? <Check size={13} /> : <Copy size={13} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-xs leading-relaxed text-ink/85">
{SNIPPET}
            </pre>
          </div>
        </div>
      </div>
    </section>
  )
}

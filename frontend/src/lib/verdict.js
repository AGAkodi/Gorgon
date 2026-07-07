import { ShieldCheck, ShieldAlert, TriangleAlert, ShieldX } from 'lucide-react'

// Single source of truth for the verdict color system.
// Used identically across hero chips, the dashboard, and the sandbox —
// never repurposed for anything else in the UI.
export const VERDICTS = {
  safe: {
    label: 'Safe',
    color: 'var(--color-verdict-safe)',
    className: 'text-verdict-safe',
    bg: 'bg-verdict-safe/10',
    border: 'border-verdict-safe/30',
    icon: ShieldCheck,
  },
  caution: {
    label: 'Caution',
    color: 'var(--color-verdict-caution)',
    className: 'text-verdict-caution',
    bg: 'bg-verdict-caution/10',
    border: 'border-verdict-caution/30',
    icon: ShieldAlert,
  },
  high_risk: {
    label: 'High Risk',
    color: 'var(--color-verdict-high_risk)',
    className: 'text-verdict-high_risk',
    bg: 'bg-verdict-high_risk/10',
    border: 'border-verdict-high_risk/30',
    icon: TriangleAlert,
  },
  critical: {
    label: 'Critical',
    color: 'var(--color-verdict-critical)',
    className: 'text-verdict-critical',
    bg: 'bg-verdict-critical/10',
    border: 'border-verdict-critical/30',
    icon: ShieldX,
  },
}

export const VERDICT_ORDER = ['safe', 'caution', 'high_risk', 'critical']

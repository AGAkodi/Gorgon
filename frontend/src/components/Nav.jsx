import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, Menu, X, ShieldHalf } from 'lucide-react'
import PillButton from './PillButton'

const DROPDOWNS = {
  PRODUCT: [
    { label: 'Verdict Engine', to: '/dashboard' },
    { label: 'Simulation Sandbox', to: '/sandbox' },
  ],
  DEVELOPERS: [
    { label: 'MCP Tools', to: '/#developers' },
    { label: 'API Reference', to: '/#developers' },
  ],
  COMPANY: [
    { label: 'About', to: '/' },
    { label: 'Contact', to: '/' },
  ],
}

const SIMPLE_LINKS = [
  { label: 'Pricing', to: '/#pricing' },
  { label: 'Docs', to: '/#developers' },
]

function NavDropdown({ label }) {
  const [open, setOpen] = useState(false)
  const items = DROPDOWNS[label]

  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-muted transition-colors hover:text-ink"
        onClick={() => setOpen((o) => !o)}
      >
        {label}
        <ChevronDown size={14} strokeWidth={2} />
      </button>
      {open && (
        <div className="absolute left-0 top-full pt-3">
          <div className="w-48 rounded-xl border border-border bg-surface p-1.5 shadow-2xl shadow-black/50">
            {items.map((item) => (
              <Link
                key={item.label}
                to={item.to}
                className="block rounded-lg px-3 py-2 text-sm text-ink/90 hover:bg-surface-2"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MobileMenu({ open, onClose }) {
  if (!open) return null

  return (
    <div className="border-t border-border px-6 py-4 lg:hidden">
      <nav className="flex flex-col gap-1">
        {Object.entries(DROPDOWNS).map(([label, items]) => (
          <div key={label} className="py-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">{label}</p>
            <div className="mt-2 flex flex-col gap-1">
              {items.map((item) => (
                <Link
                  key={item.label}
                  to={item.to}
                  onClick={onClose}
                  className="rounded-lg px-2 py-2 text-sm text-ink/90 hover:bg-surface-2"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        ))}
        <div className="mt-1 flex flex-col gap-1 border-t border-border pt-3">
          {SIMPLE_LINKS.map((link) => (
            <Link
              key={link.label}
              to={link.to}
              onClick={onClose}
              className="rounded-lg px-2 py-2 text-sm text-ink/90 hover:bg-surface-2"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  )
}

export default function Nav() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 border-b border-border/80 bg-bg/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
          <ShieldHalf size={22} strokeWidth={2.25} />
          <span className="font-display text-lg font-bold tracking-tight">Vetra</span>
        </Link>

        <nav className="hidden items-center gap-8 lg:flex">
          <NavDropdown label="PRODUCT" />
          <NavDropdown label="DEVELOPERS" />
          {SIMPLE_LINKS.map((link) => (
            <Link
              key={link.label}
              to={link.to}
              className="text-xs font-medium uppercase tracking-wider text-muted transition-colors hover:text-ink"
            >
              {link.label}
            </Link>
          ))}
          <NavDropdown label="COMPANY" />
        </nav>

        <div className="flex items-center gap-3">
          <PillButton variant="secondary" className="hidden sm:inline-flex">
            Log In
          </PillButton>
          <PillButton variant="primary">Get API Key</PillButton>
          <button
            type="button"
            onClick={() => setMobileOpen((o) => !o)}
            className="inline-flex items-center justify-center rounded-full border border-border p-2.5 text-ink lg:hidden"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      <MobileMenu open={mobileOpen} onClose={() => setMobileOpen(false)} />
    </header>
  )
}

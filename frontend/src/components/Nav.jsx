import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Menu, X, LogOut, ChevronDown } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import PillButton from './PillButton'

export default function Nav() {
  const { isConnected, walletAddress, triggerLogin, disconnect } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()

  const truncatedAddress = walletAddress
    ? `${walletAddress.slice(0, 6)}…${walletAddress.slice(-4)}`
    : ''

  const handleLinkClick = (selector) => {
    setMobileOpen(false)
    if (window.location.pathname !== '/') {
      navigate('/')
      setTimeout(() => {
        const el = document.querySelector(selector)
        if (el) el.scrollIntoView({ behavior: 'smooth' })
      }, 300)
    } else {
      const el = document.querySelector(selector)
      if (el) el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <img src="/logo.png" alt="Vetra Logo" className="w-8 h-8 object-contain group-hover:scale-105 transition-transform" />
          <span className="font-display text-xl font-black tracking-tight text-ink">Vetra</span>
        </Link>

        {/* Center Links */}
        <nav className="hidden items-center gap-8 lg:flex">
          {!isConnected ? (
            <>
              <button
                onClick={() => handleLinkClick('#how-it-works')}
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors cursor-pointer"
              >
                How It Works
              </button>
              <button
                onClick={() => handleLinkClick('#features')}
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors cursor-pointer"
              >
                Features
              </button>
              <button
                onClick={() => handleLinkClick('#pricing')}
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors cursor-pointer"
              >
                Pricing
              </button>
            </>
          ) : (
            <>
              <Link
                to="/dashboard"
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors"
              >
                Dashboard
              </Link>
              <Link
                to="/sandbox"
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors"
              >
                Sandbox
              </Link>
              <Link
                to="/api-keys"
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors"
              >
                API Keys
              </Link>
              <Link
                to="/pricing"
                className="text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink transition-colors"
              >
                Pricing
              </Link>
            </>
          )}
        </nav>

        {/* Right CTA */}
        <div className="hidden lg:flex items-center gap-3">
          {!isConnected ? (
            <PillButton as="button" onClick={triggerLogin} variant="primary" className="bg-brand text-bg font-bold">
              Get Started
            </PillButton>
          ) : (
            <div className="relative">
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-2 rounded-full border-2 border-border bg-surface px-5 py-2 font-mono text-xs font-bold text-ink hover:border-brand transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-brand" />
                {truncatedAddress}
                <ChevronDown size={14} className="text-muted" />
              </button>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 z-20 w-48 rounded-2xl border border-border bg-surface p-1.5 shadow-xl">
                    <button
                      onClick={() => {
                        setMenuOpen(false)
                        disconnect()
                      }}
                      className="w-full flex items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-semibold text-verdict-critical hover:bg-surface-2 transition-colors"
                    >
                      <LogOut size={16} />
                      Disconnect
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Mobile menu trigger */}
        <button
          type="button"
          onClick={() => setMobileOpen((o) => !o)}
          className="inline-flex items-center justify-center rounded-full border border-border p-2.5 text-ink lg:hidden hover:border-brand transition-colors"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="border-t border-border px-6 py-4 bg-bg lg:hidden">
          <nav className="flex flex-col gap-3">
            {!isConnected ? (
              <>
                <button
                  onClick={() => handleLinkClick('#how-it-works')}
                  className="text-left py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  How It Works
                </button>
                <button
                  onClick={() => handleLinkClick('#features')}
                  className="text-left py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Features
                </button>
                <button
                  onClick={() => handleLinkClick('#pricing')}
                  className="text-left py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Pricing
                </button>
                <PillButton as="button" onClick={() => { setMobileOpen(false); triggerLogin(); }} variant="primary" className="w-full text-center py-3">
                  Get Started
                </PillButton>
              </>
            ) : (
              <>
                <Link
                  to="/dashboard"
                  onClick={() => setMobileOpen(false)}
                  className="py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Dashboard
                </Link>
                <Link
                  to="/sandbox"
                  onClick={() => setMobileOpen(false)}
                  className="py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Sandbox
                </Link>
                <Link
                  to="/api-keys"
                  onClick={() => setMobileOpen(false)}
                  className="py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  API Keys
                </Link>
                <Link
                  to="/pricing"
                  onClick={() => setMobileOpen(false)}
                  className="py-2 text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Pricing
                </Link>
                <button
                  onClick={() => {
                    setMobileOpen(false)
                    disconnect()
                  }}
                  className="w-full flex items-center gap-2 rounded-xl py-3 text-sm font-semibold text-verdict-critical hover:bg-surface-2 transition-colors"
                >
                  <LogOut size={16} />
                  Disconnect ({truncatedAddress})
                </button>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  )
}

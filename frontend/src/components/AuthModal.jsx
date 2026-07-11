import { useAuth } from '../context/AuthContext'
import { X, ShieldAlert, KeyRound, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function AuthModal() {
  const {
    showAuthModal,
    setShowAuthModal,
    isSigning,
    selectedWallet,
    connectWallet,
    signMessage,
  } = useAuth()

  if (!showAuthModal) return null

  const siweMessage = `Sign-in Request for Vetra Sandbox
Domain: vetra.sandbox
Address: 0x4a2f8d3c267c5d32be8058bb8eb970870f07c91e
Statement: I prove ownership of this wallet and sign in to Vetra.
Nonce: 9812401
Issued At: ${new Date().toISOString()}
Chain ID: 1952 (X Layer)`

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/40 backdrop-blur-xs"
          onClick={() => {
            if (!isSigning) setShowAuthModal(false)
          }}
        />

        {/* Modal content Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ duration: 0.2 }}
          className="relative z-10 w-full max-w-md rounded-3xl border-2 border-border bg-bg p-6 text-ink shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-bold uppercase tracking-tight flex items-center gap-2">
              <KeyRound className="text-brand" size={20} />
              Verify Wallet Identity
            </h3>
            {!isSigning && (
              <button
                onClick={() => setShowAuthModal(false)}
                className="rounded-full border border-border p-1.5 text-muted hover:border-ink hover:text-ink transition-colors"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <p className="mt-2 text-xs text-muted">
            Vetra uses cryptographically secure wallet authentication for logs, API keys, and billing.
          </p>

          <hr className="my-4 border-border" />

          {/* Body */}
          {!selectedWallet ? (
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-1">
                Select Your Wallet on X Layer
              </p>
              <button
                onClick={() => connectWallet('OKX Wallet')}
                className="w-full flex items-center justify-between rounded-2xl border border-border bg-surface px-5 py-4 font-display text-sm font-bold hover:border-brand hover:bg-surface-2 transition-all group"
              >
                <span className="flex items-center gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-brand" />
                  OKX Wallet
                </span>
                <span className="text-xs font-mono font-normal text-muted group-hover:text-brand transition-colors">
                  Fast Connection
                </span>
              </button>

              <button
                onClick={() => connectWallet('WalletConnect')}
                className="w-full flex items-center justify-between rounded-2xl border border-border bg-surface px-5 py-4 font-display text-sm font-bold hover:border-brand hover:bg-surface-2 transition-all group"
              >
                <span className="flex items-center gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#3b99fc]" />
                  WalletConnect
                </span>
                <span className="text-xs font-mono font-normal text-muted group-hover:text-brand transition-colors">
                  Any Wallet
                </span>
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-xl border border-border bg-surface p-4">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted mb-2">
                  SIWE Signature Message
                </p>
                <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-ink/80 bg-bg p-3 rounded-lg border border-border max-h-48 overflow-y-auto">
                  {siweMessage}
                </pre>
              </div>

              {isSigning ? (
                <div className="flex flex-col items-center justify-center py-4">
                  <Loader2 className="animate-spin text-brand mb-2" size={28} />
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Requesting signature from {selectedWallet}...
                  </p>
                  <p className="text-[10px] text-muted mt-1">
                    Please approve the request in your wallet window.
                  </p>
                </div>
              ) : (
                <button
                  onClick={signMessage}
                  className="w-full rounded-full bg-brand py-3.5 font-display text-sm font-bold text-bg hover:opacity-90 transition-all shadow-md shadow-brand/20"
                >
                  Sign SIWE Message
                </button>
              )}
            </div>
          )}

          {/* Footer note */}
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-surface p-3 border border-border">
            <ShieldAlert className="text-brand shrink-0 mt-0.5" size={14} />
            <p className="text-[10px] text-muted leading-normal">
              <strong>Security Note:</strong> Sign-In with Ethereum (SIWE) is gasless. It creates a local session key and will never spend your assets or reveal private keys.
            </p>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import PillButton from '../components/PillButton'
import { ShieldAlert, Copy, Check, Plus, Trash2, KeyRound, Eye } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function ApiKeys() {
  const { isConnected, triggerLogin, walletAddress } = useAuth()
  const [keys, setKeys] = useState([])
  const [copiedId, setCopiedId] = useState(null)
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState(null) // Once-only exposure key

  const fetchKeys = async () => {
    try {
      const token = localStorage.getItem('vetra_session_token')
      const resp = await fetch('http://localhost:4023/api/api-keys', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (resp.ok) {
        const data = await resp.json()
        setKeys(data)
      }
    } catch (err) {
      console.error('Failed to load API keys:', err)
    }
  }

  useEffect(() => {
    if (isConnected) {
      fetchKeys()
    }
  }, [isConnected])

  const handleCopy = (id, keyText) => {
    navigator.clipboard.writeText(keyText)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleGenerate = async (e) => {
    e.preventDefault()
    if (!newKeyName) return
    try {
      const token = localStorage.getItem('vetra_session_token')
      const resp = await fetch('http://localhost:4023/api/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ label: newKeyName })
      })

      if (!resp.ok) {
        throw new Error('Failed to generate key')
      }

      const data = await resp.json()
      setCreatedKey(data.raw_key)
      setNewKeyName('')
      fetchKeys()
    } catch (err) {
      console.error(err)
      alert('Key creation failed: ' + err.message)
    }
  }

  const handleDelete = async (keyHash) => {
    if (!confirm('Are you sure you want to revoke this API key? This action is irreversible.')) return
    try {
      const token = localStorage.getItem('vetra_session_token')
      const resp = await fetch(`http://localhost:4023/api/api-keys/${keyHash}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (resp.ok) {
        fetchKeys()
      } else {
        throw new Error('Revoke failed')
      }
    } catch (err) {
      console.error(err)
      alert('Failed to revoke API key: ' + err.message)
    }
  }

  if (!isConnected) {
    return (
      <div className="min-h-screen bg-bg text-ink flex flex-col justify-between">
        <Nav />
        <main className="flex-1 flex items-center justify-center px-6 py-20">
          <div className="max-w-md w-full rounded-3xl border-2 border-border bg-surface p-8 text-center shadow-xl relative overflow-hidden">
            <div className="absolute -top-3 -right-3 w-6 h-6 border border-border bg-bg rotate-45" />
            <div className="absolute -bottom-3 -left-3 w-6 h-6 border border-border bg-bg rotate-45" />

            <div className="mx-auto w-12 h-12 rounded-full border border-border bg-bg flex items-center justify-center text-brand mb-4">
              <KeyRound size={24} />
            </div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">Access Gated</h2>
            <p className="mt-3 text-sm text-muted leading-relaxed">
              Vetra's developer dashboards and API credentials are tied directly to your wallet identity. Connect your wallet via SIWE to proceed.
            </p>
            <div className="mt-6">
              <PillButton as="button" onClick={triggerLogin} variant="primary" className="w-full">
                Connect Wallet
              </PillButton>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col justify-between">
      <Nav />
      <main className="flex-grow mx-auto max-w-4xl w-full px-6 py-14">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          Developer Suite
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          API Credentials
        </h1>
        <p className="mt-2 text-sm text-muted">
          Generate and manage security keys to query Vetra consensus verdicts and sandbox simulations programmatically.
        </p>

        {/* Generate New Key Form */}
        <form onSubmit={handleGenerate} className="mt-8 rounded-3xl border border-border bg-surface p-6">
          <h3 className="font-display text-base font-bold tracking-tight">Generate New Key</h3>
          <div className="mt-4 flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="e.g. Production Auto-Verifier"
              className="flex-1 rounded-full border border-border bg-bg px-5 py-3 text-sm text-ink outline-none focus:border-brand transition-colors placeholder:text-muted"
              required
            />
            <PillButton as="button" type="submit" variant="primary" className="whitespace-nowrap flex items-center justify-center gap-1.5">
              <Plus size={16} />
              Create Key
            </PillButton>
          </div>
        </form>

        {/* Keys List */}
        <div className="mt-8 rounded-3xl border border-border bg-surface overflow-hidden">
          <div className="px-6 py-5 border-b border-border flex items-center justify-between">
            <h3 className="font-display text-base font-bold tracking-tight">Active API Keys</h3>
            <span className="font-mono text-xs text-muted">Wallet: {walletAddress.slice(0, 6)}…{walletAddress.slice(-4)}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-2/40 text-[10px] font-semibold uppercase tracking-wider text-muted">
                  <th className="px-6 py-3.5">Key Name</th>
                  <th className="px-6 py-3.5">API Key Hash</th>
                  <th className="px-6 py-3.5 text-right">Created At</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {keys.map((k) => (
                  <tr key={k.key} className="text-sm hover:bg-surface-2/30 transition-colors">
                    <td className="px-6 py-4.5 font-medium text-ink/90">
                      {k.label}
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs bg-bg border border-border px-2.5 py-1 rounded-md text-muted select-all">
                          {k.key.slice(0, 8)}…{k.key.slice(-8)}
                        </span>
                        <button
                          onClick={() => handleCopy(k.key, k.key)}
                          className="text-muted hover:text-brand transition-colors p-1"
                          title="Copy Key Hash"
                        >
                          {copiedId === k.key ? <Check size={14} className="text-[#10B981]" /> : <Copy size={14} />}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4.5 text-right font-mono text-xs text-ink/80">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4.5 text-right">
                      <button
                        onClick={() => handleDelete(k.key)}
                        className="text-muted hover:text-verdict-critical transition-colors p-1"
                        title="Revoke Key"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
                {keys.length === 0 && (
                  <tr>
                    <td colSpan="4" className="px-6 py-10 text-center text-sm text-muted">
                      No active API keys found. Create one above to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Once-only raw key display Modal */}
        <AnimatePresence>
          {createdKey && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/30 backdrop-blur-xs"
                onClick={() => setCreatedKey(null)}
              />
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 8 }}
                className="relative z-10 w-full max-w-md rounded-3xl border border-border bg-surface p-6 shadow-2xl text-ink"
              >
                <div className="flex items-center gap-2 text-brand">
                  <Eye size={20} />
                  <h3 className="font-display text-base font-black uppercase tracking-tight">API Key Generated</h3>
                </div>
                <p className="mt-3 text-xs text-muted leading-relaxed">
                  Please copy this key and store it securely. For security, it will only be displayed <strong>once</strong>.
                </p>
                <div className="mt-4 flex items-center justify-between rounded-xl bg-bg border border-border px-4 py-3">
                  <span className="font-mono text-xs select-all break-all text-ink/90">{createdKey}</span>
                  <button
                    onClick={() => handleCopy('new_key', createdKey)}
                    className="text-muted hover:text-brand transition-colors p-1 flex-shrink-0 ml-2"
                  >
                    {copiedId === 'new_key' ? <Check size={16} className="text-[#10B981]" /> : <Copy size={16} />}
                  </button>
                </div>
                <div className="mt-6">
                  <PillButton as="button" onClick={() => setCreatedKey(null)} variant="primary" className="w-full font-bold uppercase tracking-wider text-xs py-3">
                    I Have Stored the Key
                  </PillButton>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Integration Alert */}
        <div className="mt-6 flex items-start gap-3 rounded-2xl bg-surface p-4 border border-border">
          <ShieldAlert className="text-brand shrink-0 mt-0.5" size={16} />
          <div className="text-xs leading-normal">
            <p className="font-bold text-ink/90">Consensus Gating Integration</p>
            <p className="text-muted mt-1">
              API queries deduct dynamically from your wallet balance on a pay-per-call basis. Revoke unused keys immediately to safeguard your associated wallet identity credentials.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}


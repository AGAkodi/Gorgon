import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getInjectedProvider, ensureXLayerChain } from '../lib/xlayer'
import { API_BASE_URL } from '../lib/api'

const AuthContext = createContext()

// fetch() throws a generic "Failed to fetch" / "NetworkError" with no useful
// detail when the server simply isn't running — this turns that into an
// actionable message instead of leaving whoever hits it to guess.
async function fetchAuthServer(path, options) {
  try {
    return await fetch(`${API_BASE_URL}${path}`, options)
  } catch (err) {
    throw new Error(
      `Could not reach the Vetra auth server at ${API_BASE_URL}. ` +
      `Make sure it's running: python3 mcp-server/auth_server.py`
    )
  }
}

export function AuthProvider({ children }) {
  const [walletAddress, setWalletAddress] = useState(() => localStorage.getItem('vetra_wallet_address'))
  const [sessionToken, setSessionToken] = useState(() => localStorage.getItem('vetra_session_token'))
  const [isSigning, setIsSigning] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [selectedWallet, setSelectedWallet] = useState(null)
  const [pendingSiweMessage, setPendingSiweMessage] = useState(null)
  const [authError, setAuthError] = useState(null)
  const navigate = useNavigate()

  const isConnected = !!walletAddress && !!sessionToken

  const triggerLogin = () => {
    // "Get Started" goes straight to OKX Wallet — no wallet-picker step for
    // the primary path. The modal still opens to show connection/signing
    // progress, with a fallback link inside it for other injected wallets.
    setShowAuthModal(true)
    connectWallet('OKX Wallet')
  }

  const connectWallet = (walletName) => {
    setAuthError(null)
    setSelectedWallet(walletName)
    setIsSigning(true)
    // Trigger signature request immediately
    setTimeout(() => {
      signMessage(walletName)
    }, 100)
  }

  const signMessage = async (walletName = selectedWallet) => {
    try {
      const preferOkx = walletName !== 'Other Wallet'
      const provider = getInjectedProvider(preferOkx)

      if (!provider) {
        // Surface the reason in the modal and drop back to the wallet picker
        // instead of alert()-ing and leaving a dead "waiting..." state.
        setAuthError(
          preferOkx
            ? 'OKX Wallet not detected in this browser. Install it from okx.com/web3, or choose "Other Wallet" if you have a different EVM wallet (MetaMask, Rabby, …).'
            : 'No EVM wallet detected in this browser. Install a wallet extension (OKX Wallet, MetaMask, …) and try again.'
        )
        setIsSigning(false)
        setSelectedWallet(null)
        return
      }

      // 1. Get wallet address
      const accounts = await provider.request({ method: 'eth_requestAccounts' })
      if (!accounts || accounts.length === 0) {
        throw new Error('No accounts returned from wallet')
      }
      const address = accounts[0]

      // 2. Confirm/switch to X Layer before going any further
      await ensureXLayerChain(provider)

      // 3. Request SIWE message/nonce from auth server
      const nonceResp = await fetchAuthServer(`/api/auth/nonce?address=${address}`)
      if (!nonceResp.ok) {
        throw new Error('Failed to retrieve authentication nonce from server')
      }
      const { message } = await nonceResp.json()
      setPendingSiweMessage(message)

      // 4. Request signature from wallet
      const signature = await provider.request({
        method: 'personal_sign',
        params: [message, address],
      })

      // 5. Send signature to server
      const loginResp = await fetchAuthServer('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          address,
          message,
          signature,
        }),
      })

      if (!loginResp.ok) {
        throw new Error('Signature verification failed on auth server')
      }

      const { token, walletAddress: verifiedAddress } = await loginResp.json()

      // 6. Store session and transition UI
      localStorage.setItem('vetra_session_token', token)
      localStorage.setItem('vetra_wallet_address', verifiedAddress)
      setWalletAddress(verifiedAddress)
      setSessionToken(token)
      setShowAuthModal(false)
      setIsSigning(false)
      setSelectedWallet(null)
      setPendingSiweMessage(null)
      navigate('/dashboard')
    } catch (err) {
      console.error('Wallet authentication failure:', err)
      // Common case: user rejected the request in their wallet (code 4001).
      const msg =
        err?.code === 4001
          ? 'Connection request was rejected in your wallet. Try again and approve it.'
          : err?.message || 'Authentication failed. Please try again.'
      setAuthError(msg)
      setIsSigning(false)
      setSelectedWallet(null)
      setPendingSiweMessage(null)
    }
  }

  const disconnect = () => {
    localStorage.removeItem('vetra_session_token')
    localStorage.removeItem('vetra_wallet_address')
    setWalletAddress(null)
    setSessionToken(null)
    setSelectedWallet(null)
    setIsSigning(false)
    navigate('/')
  }

  return (
    <AuthContext.Provider
      value={{
        walletAddress,
        sessionToken,
        isConnected,
        isSigning,
        showAuthModal,
        selectedWallet,
        pendingSiweMessage,
        authError,
        closeAuthModal: () => {
          setShowAuthModal(false)
          setAuthError(null)
          setSelectedWallet(null)
          setIsSigning(false)
        },
        setShowAuthModal,
        triggerLogin,
        connectWallet,
        useOtherWallet: () => connectWallet('Other Wallet'),
        signMessage,
        disconnect,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}


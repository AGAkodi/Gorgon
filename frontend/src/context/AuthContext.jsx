import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [walletAddress, setWalletAddress] = useState(() => localStorage.getItem('vetra_wallet_address'))
  const [sessionToken, setSessionToken] = useState(() => localStorage.getItem('vetra_session_token'))
  const [isSigning, setIsSigning] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [selectedWallet, setSelectedWallet] = useState(null)
  const navigate = useNavigate()

  const isConnected = !!walletAddress && !!sessionToken

  const triggerLogin = () => {
    setShowAuthModal(true)
    setSelectedWallet(null)
    setIsSigning(false)
  }

  const connectWallet = (walletName) => {
    setSelectedWallet(walletName)
    setIsSigning(true)
    // Trigger signature request immediately
    setTimeout(() => {
      signMessage()
    }, 100)
  }

  const signMessage = async () => {
    try {
      if (!window.ethereum) {
        alert('No EVM wallet detected. Please install OKX Wallet.')
        setIsSigning(false)
        return
      }

      // 1. Get wallet address
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
      if (!accounts || accounts.length === 0) {
        throw new Error('No accounts returned from wallet')
      }
      const address = accounts[0]

      // 2. Request SIWE message/nonce from auth server
      const nonceResp = await fetch(`http://localhost:4023/api/auth/nonce?address=${address}`)
      if (!nonceResp.ok) {
        throw new Error('Failed to retrieve authentication nonce from server')
      }
      const { message } = await nonceResp.json()

      // 3. Request signature from wallet
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [message, address],
      })

      // 4. Send signature to server
      const loginResp = await fetch('http://localhost:4023/api/auth/login', {
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

      // 5. Store session and transition UI
      localStorage.setItem('vetra_session_token', token)
      localStorage.setItem('vetra_wallet_address', verifiedAddress)
      setWalletAddress(verifiedAddress)
      setSessionToken(token)
      setShowAuthModal(false)
      setIsSigning(false)
      setSelectedWallet(null)
      navigate('/dashboard')
    } catch (err) {
      console.error('Wallet authentication failure:', err)
      alert(err.message || 'Authentication failed. Please try again.')
      setIsSigning(false)
      setSelectedWallet(null)
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
        setShowAuthModal,
        triggerLogin,
        connectWallet,
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


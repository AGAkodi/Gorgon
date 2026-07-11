import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Sandbox from './pages/Sandbox'
import ApiKeys from './pages/ApiKeys'
import PricingPage from './pages/PricingPage'
import AuthModal from './components/AuthModal'

function App() {
  return (
    <AuthProvider>
      {/* Obscura Page-Edge Decorative Framing */}
      <div className="page-edge-frame" />
      <div className="floating-square-chip" style={{ top: '8px', left: '8px' }} />
      <div className="floating-square-chip" style={{ top: '8px', right: '8px' }} />
      <div className="floating-square-chip" style={{ bottom: '8px', left: '8px' }} />
      <div className="floating-square-chip" style={{ bottom: '8px', right: '8px' }} />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/sandbox" element={<Sandbox />} />
        <Route path="/api-keys" element={<ApiKeys />} />
        <Route path="/pricing" element={<PricingPage />} />
      </Routes>
      <AuthModal />
    </AuthProvider>
  )
}

export default App

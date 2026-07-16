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

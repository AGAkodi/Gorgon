import Nav from '../components/Nav'
import Footer from '../components/Footer'
import Hero from '../sections/Hero'
import HowItWorks from '../sections/HowItWorks'
import FeatureBreakdown from '../sections/FeatureBreakdown'
import ChainSupport from '../sections/ChainSupport'
import PricingPreview from '../sections/PricingPreview'

export default function Home() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <FeatureBreakdown />
        <ChainSupport />
        <PricingPreview />
      </main>
      <Footer />
    </div>
  )
}

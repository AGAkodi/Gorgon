import Nav from '../components/Nav'
import Footer from '../components/Footer'
import Hero from '../sections/Hero'
import HowItWorks from '../sections/HowItWorks'
import ForDevelopers from '../sections/ForDevelopers'
import ChainSupport from '../sections/ChainSupport'

export default function Home() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <ForDevelopers />
        <ChainSupport />
      </main>
      <Footer />
    </div>
  )
}

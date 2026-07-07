import { useEffect, useRef, useState } from 'react'
import { sessionFlags } from '../state/sessionFlags'

const WIDTH = 1200
const HEIGHT = 260
const CENTER = 130

// Builds a closed band shape (top edge + bottom edge) so the ribbon reads as
// a twisting 3D surface rather than a flat line: local thickness is
// modulated by a second, out-of-phase wave to fake the twist catching light.
function buildRibbonPath(stage, phase) {
  const jagged = stage === 'jagged'
  const samples = jagged ? 20 : 90
  const amplitude = jagged ? 34 : 28
  const baseThickness = 22

  const top = []
  const bottom = []

  for (let i = 0; i <= samples; i++) {
    const t = i / samples
    const x = t * WIDTH
    const wave = Math.sin(t * Math.PI * 2.4 + phase)
    let center = CENTER + amplitude * wave

    if (jagged) {
      const hash = Math.sin(i * 12.9898 + phase * 3.1) * 43758.5453
      const frac = hash - Math.floor(hash)
      center += (frac - 0.5) * 48
    }

    const twist = Math.cos(t * Math.PI * 2.4 * 1.4 + phase * 0.7)
    const half = baseThickness * (0.3 + 0.7 * Math.abs(twist))

    top.push([x, center - half])
    bottom.push([x, center + half])
  }

  let d = `M ${top[0][0].toFixed(1)},${top[0][1].toFixed(1)} `
  for (let i = 1; i < top.length; i++) {
    d += `L ${top[i][0].toFixed(1)},${top[i][1].toFixed(1)} `
  }
  for (let i = bottom.length - 1; i >= 0; i--) {
    d += `L ${bottom[i][0].toFixed(1)},${bottom[i][1].toFixed(1)} `
  }
  d += 'Z'
  return d
}

export default function Ribbon({ className = '' }) {
  const containerRef = useRef(null)
  const pathRef = useRef(null)
  const glowRef = useRef(null)
  const stageRef = useRef(sessionFlags.ribbonMorphed ? 'safe' : 'mono')
  const [stage, setStage] = useState(stageRef.current)
  const phaseRef = useRef(0)
  const hasTriggeredRef = useRef(sessionFlags.ribbonMorphed)

  // Continuous slow undulation, independent of stage — mutated directly on
  // the DOM via rAF rather than React state so it never re-renders at 60fps.
  useEffect(() => {
    let raf
    const tick = () => {
      phaseRef.current += 0.0055
      const d = buildRibbonPath(stageRef.current, phaseRef.current)
      if (pathRef.current) pathRef.current.setAttribute('d', d)
      if (glowRef.current) glowRef.current.setAttribute('d', d)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  // One-shot scroll-into-view trigger, guarded by module-scoped session state.
  useEffect(() => {
    if (hasTriggeredRef.current) return undefined
    const el = containerRef.current
    if (!el) return undefined

    let resolveTimeout

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !hasTriggeredRef.current) {
            hasTriggeredRef.current = true
            sessionFlags.ribbonMorphed = true
            stageRef.current = 'jagged'
            setStage('jagged')

            resolveTimeout = setTimeout(() => {
              stageRef.current = 'safe'
              setStage('safe')
            }, 750)

            io.disconnect()
          }
        }
      },
      { threshold: 0.4 },
    )

    io.observe(el)
    return () => {
      io.disconnect()
      if (resolveTimeout) clearTimeout(resolveTimeout)
    }
  }, [])

  const fill =
    stage === 'jagged'
      ? 'var(--color-verdict-critical)'
      : stage === 'safe'
        ? 'var(--color-verdict-safe)'
        : 'url(#ribbon-mono-gradient)'

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        className="h-[160px] w-full sm:h-[200px] lg:h-[240px]"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="ribbon-mono-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#f4f4f5" />
            <stop offset="45%" stopColor="#616167" />
            <stop offset="100%" stopColor="#f4f4f5" />
          </linearGradient>
          <filter id="ribbon-blur" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="16" />
          </filter>
        </defs>
        <path
          ref={glowRef}
          fill={fill}
          filter="url(#ribbon-blur)"
          opacity="0.35"
          style={{ transition: 'fill 500ms ease' }}
        />
        <path ref={pathRef} fill={fill} style={{ transition: 'fill 500ms ease' }} />
      </svg>
    </div>
  )
}

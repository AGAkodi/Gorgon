import { useEffect, useState } from 'react'

// Animates a number from 0 to `target` once on mount. Used for the sandbox
// balance-delta chip and dashboard confidence readouts — small, functional,
// not a "showcase" animation.
export function useCountTo(target, { duration = 1100, delay = 300 } = {}) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    let raf
    let start
    const timeout = setTimeout(() => {
      const tick = (ts) => {
        if (start === undefined) start = ts
        const elapsed = ts - start
        const progress = Math.min(elapsed / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3)
        setValue(target * eased)
        if (progress < 1) raf = requestAnimationFrame(tick)
      }
      raf = requestAnimationFrame(tick)
    }, delay)

    return () => {
      clearTimeout(timeout)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [target, duration, delay])

  return value
}

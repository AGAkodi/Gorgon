import { Link } from 'react-router-dom'

const base =
  'inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium tracking-tight transition-colors duration-200 whitespace-nowrap'

const variants = {
  primary: 'bg-ink text-bg hover:bg-white',
  secondary: 'border border-border text-ink hover:border-ink/60 bg-transparent',
}

export default function PillButton({
  as,
  to,
  href,
  variant = 'primary',
  className = '',
  children,
  ...props
}) {
  const classes = `${base} ${variants[variant]} ${className}`

  if (to) {
    return (
      <Link to={to} className={classes} {...props}>
        {children}
      </Link>
    )
  }

  if (href) {
    return (
      <a href={href} className={classes} {...props}>
        {children}
      </a>
    )
  }

  const Comp = as || 'button'
  return (
    <Comp className={classes} {...props}>
      {children}
    </Comp>
  )
}

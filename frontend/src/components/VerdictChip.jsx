import { VERDICTS } from '../lib/verdict'

const sizes = {
  sm: 'text-xs px-2.5 py-1 gap-1',
  md: 'text-sm px-3.5 py-1.5 gap-1.5',
  lg: 'text-base px-5 py-2.5 gap-2',
}

const iconSizes = { sm: 14, md: 16, lg: 20 }

export default function VerdictChip({ verdict, size = 'md', className = '' }) {
  const v = VERDICTS[verdict]
  if (!v) return null
  const Icon = v.icon

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium ${v.bg} ${v.border} ${v.className} ${sizes[size]} ${className}`}
    >
      <Icon size={iconSizes[size]} strokeWidth={2.25} />
      {v.label}
    </span>
  )
}

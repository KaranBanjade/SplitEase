import { cn } from '@/lib/utils'

type BadgeColor = 'green' | 'red' | 'yellow' | 'blue' | 'gray' | 'purple'

interface BadgeProps {
  children: React.ReactNode
  color?: BadgeColor
  className?: string
}

const colorMap: Record<BadgeColor, string> = {
  green: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/25',
  red: 'bg-red-500/15 text-red-400 ring-red-500/25',
  yellow: 'bg-amber-500/15 text-amber-400 ring-amber-500/25',
  blue: 'bg-blue-500/15 text-blue-400 ring-blue-500/25',
  gray: 'bg-slate-500/15 text-slate-400 ring-slate-500/25',
  purple: 'bg-primary-500/15 text-primary-400 ring-primary-500/25',
}

export function Badge({
  children,
  color = 'gray',
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        colorMap[color],
        className
      )}
    >
      {children}
    </span>
  )
}

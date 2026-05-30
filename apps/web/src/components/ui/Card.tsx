import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  onClick?: () => void
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const paddingMap = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
}

export function Card({
  children,
  className,
  onClick,
  padding = 'md',
}: CardProps) {
  const base = cn(
    'bg-slate-800 rounded-2xl border border-slate-700/50',
    paddingMap[padding],
    className
  )

  if (onClick) {
    return (
      <motion.div
        whileTap={{ scale: 0.98 }}
        className={cn(base, 'cursor-pointer hover:bg-slate-750 hover:border-slate-600 transition-colors active:bg-slate-700')}
        onClick={onClick}
      >
        {children}
      </motion.div>
    )
  }

  return <div className={base}>{children}</div>
}

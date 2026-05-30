import { cn, getInitials } from '@/lib/utils'

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

interface AvatarProps {
  name: string
  src?: string
  size?: AvatarSize
  className?: string
}

const sizeMap: Record<AvatarSize, { container: string; text: string; img: string }> = {
  xs: { container: 'w-6 h-6', text: 'text-[10px]', img: 'w-6 h-6' },
  sm: { container: 'w-8 h-8', text: 'text-xs', img: 'w-8 h-8' },
  md: { container: 'w-10 h-10', text: 'text-sm', img: 'w-10 h-10' },
  lg: { container: 'w-12 h-12', text: 'text-base', img: 'w-12 h-12' },
  xl: { container: 'w-16 h-16', text: 'text-xl', img: 'w-16 h-16' },
}

const colors = [
  'bg-violet-600',
  'bg-blue-600',
  'bg-emerald-600',
  'bg-amber-600',
  'bg-rose-600',
  'bg-cyan-600',
  'bg-fuchsia-600',
  'bg-indigo-600',
]

function getColorFromName(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

export function Avatar({ name, src, size = 'md', className }: AvatarProps) {
  const { container, text, img } = sizeMap[size]
  const initials = getInitials(name)
  const bgColor = getColorFromName(name)

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className={cn('rounded-full object-cover', img, className)}
      />
    )
  }

  return (
    <div
      className={cn(
        'rounded-full flex items-center justify-center font-semibold text-white shrink-0',
        container,
        bgColor,
        className
      )}
      title={name}
    >
      <span className={text}>{initials}</span>
    </div>
  )
}

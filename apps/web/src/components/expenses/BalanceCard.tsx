import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { Balance } from '@/types'
import { formatCurrency, cn } from '@/lib/utils'
import { Avatar } from '@/components/ui/Avatar'
import { useAuthStore } from '@/store/authStore'

interface BalanceCardProps {
  balance: Balance
  currency?: string
}

export function BalanceCard({ balance, currency = 'INR' }: BalanceCardProps) {
  const currentUserId = useAuthStore((s) => s.user?.id)
  const isCurrentUser = balance.userId === currentUserId
  const isPositive = balance.amount > 0
  const isNegative = balance.amount < 0
  const isZero = balance.amount === 0

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3.5 rounded-2xl border transition-colors',
        isPositive
          ? 'bg-emerald-500/5 border-emerald-500/20'
          : isNegative
          ? 'bg-red-500/5 border-red-500/20'
          : 'bg-slate-800 border-slate-700/50'
      )}
    >
      <Avatar
        name={balance.user.name}
        src={balance.user.avatarUrl}
        size="md"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-100 truncate">
          {isCurrentUser ? 'You' : balance.user.name}
        </p>
        <p className="text-xs text-slate-500">
          {isPositive ? 'gets back' : isNegative ? 'owes' : 'settled up'}
        </p>
      </div>
      <div className="flex items-center gap-1.5">
        {isPositive && <TrendingUp size={16} className="text-emerald-400" />}
        {isNegative && <TrendingDown size={16} className="text-red-400" />}
        {isZero && <Minus size={16} className="text-slate-500" />}
        <span
          className={cn(
            'text-sm font-semibold',
            isPositive
              ? 'text-emerald-400'
              : isNegative
              ? 'text-red-400'
              : 'text-slate-500'
          )}
        >
          {formatCurrency(Math.abs(balance.amount), currency)}
        </span>
      </div>
    </div>
  )
}

export function BalanceCardSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse">
      <div className="w-10 h-10 rounded-full bg-slate-700 shrink-0" />
      <div className="flex-1">
        <div className="h-4 bg-slate-700 rounded w-1/2 mb-2" />
        <div className="h-3 bg-slate-700 rounded w-1/3" />
      </div>
      <div className="h-4 bg-slate-700 rounded w-16" />
    </div>
  )
}

import { ArrowRight, CheckCircle2 } from 'lucide-react'
import type { SimplifiedDebt } from '@/types'
import { formatCurrency } from '@/lib/utils'
import { Avatar } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { useAuthStore } from '@/store/authStore'
import { useCreateSettlement } from '@/hooks/useSettlements'
import { cn } from '@/lib/utils'

interface DebtSimplificationViewProps {
  debts: SimplifiedDebt[]
  groupId: string
  isLoading?: boolean
}

export function DebtSimplificationView({
  debts,
  groupId,
  isLoading,
}: DebtSimplificationViewProps) {
  const currentUserId = useAuthStore((s) => s.user?.id)
  const { mutate: createSettlement, isPending } = useCreateSettlement()

  const handleSettle = (debt: SimplifiedDebt) => {
    createSettlement({
      groupId,
      paidBy: debt.fromUserId,
      paidTo: debt.toUserId,
      amount: debt.amount,
      currency: debt.currency,
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex items-center gap-3 p-4 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse"
          >
            <div className="w-10 h-10 rounded-full bg-slate-700" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-slate-700 rounded w-3/4" />
              <div className="h-3 bg-slate-700 rounded w-1/2" />
            </div>
            <div className="w-16 h-8 bg-slate-700 rounded-xl" />
          </div>
        ))}
      </div>
    )
  }

  if (debts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-4">
          <CheckCircle2 size={28} className="text-emerald-400" />
        </div>
        <p className="text-slate-300 font-medium mb-1">All settled up!</p>
        <p className="text-slate-500 text-sm">No outstanding debts in this group</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {debts.map((debt, index) => {
        const isMyDebt = debt.fromUserId === currentUserId
        const isOwedToMe = debt.toUserId === currentUserId

        return (
          <div
            key={index}
            className={cn(
              'flex items-center gap-3 p-4 rounded-2xl border',
              isMyDebt
                ? 'bg-red-500/5 border-red-500/20'
                : isOwedToMe
                ? 'bg-emerald-500/5 border-emerald-500/20'
                : 'bg-slate-800 border-slate-700/50'
            )}
          >
            <Avatar
              name={debt.fromUser.name}
              src={debt.fromUser.avatarUrl}
              size="sm"
            />
            <ArrowRight
              size={14}
              className={cn(
                'shrink-0',
                isMyDebt ? 'text-red-400' : 'text-slate-500'
              )}
            />
            <Avatar
              name={debt.toUser.name}
              src={debt.toUser.avatarUrl}
              size="sm"
            />

            <div className="flex-1 min-w-0 ml-1">
              <p className="text-sm font-medium text-slate-100 truncate">
                {isMyDebt ? 'You' : debt.fromUser.name}{' '}
                <span className="text-slate-400">owe</span>{' '}
                {isOwedToMe ? 'you' : debt.toUser.name}
              </p>
              <p
                className={cn(
                  'text-base font-semibold',
                  isMyDebt ? 'text-red-400' : 'text-emerald-400'
                )}
              >
                {formatCurrency(debt.amount, debt.currency)}
              </p>
            </div>

            {isMyDebt && (
              <Button
                size="sm"
                variant="primary"
                loading={isPending}
                onClick={() => handleSettle(debt)}
              >
                Settle
              </Button>
            )}
          </div>
        )
      })}
    </div>
  )
}

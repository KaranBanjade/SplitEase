import { motion } from 'framer-motion'
import { Receipt, ArrowUpRight, ArrowDownLeft } from 'lucide-react'
import type { Expense } from '@/types'
import { formatCurrency, formatDate, getCategoryIcon } from '@/lib/utils'
import { Avatar } from '@/components/ui/Avatar'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

interface ExpenseCardProps {
  expense: Expense
  onClick?: () => void
}

export function ExpenseCard({ expense, onClick }: ExpenseCardProps) {
  const currentUserId = useAuthStore((s) => s.user?.id)

  const myShare = expense.splits.find((s) => s.userId === currentUserId)
  const isPaidByMe = expense.paidBy === currentUserId
  const isSettled = myShare?.settledAt !== undefined

  const getBalanceInfo = () => {
    if (!currentUserId) return null
    if (isPaidByMe) {
      const othersOwe = expense.splits
        .filter((s) => s.userId !== currentUserId)
        .reduce((sum, s) => sum + s.owedAmount, 0)
      if (othersOwe > 0) {
        return { type: 'lent', amount: othersOwe, label: 'you lent' }
      }
      return null
    }
    if (myShare && !isSettled) {
      return { type: 'owe', amount: myShare.owedAmount, label: 'you owe' }
    }
    return null
  }

  const balanceInfo = getBalanceInfo()

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 p-3.5 rounded-2xl bg-slate-800 border border-slate-700/50',
        onClick && 'cursor-pointer hover:bg-slate-750 active:bg-slate-700 transition-colors'
      )}
    >
      <div className="w-10 h-10 rounded-xl bg-slate-700 flex items-center justify-center text-lg shrink-0">
        {getCategoryIcon(expense.category)}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-100 truncate">
              {expense.description}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Avatar
                name={expense.paidByUser.name}
                src={expense.paidByUser.avatarUrl}
                size="xs"
              />
              <span className="text-xs text-slate-400 truncate">
                {isPaidByMe ? 'You' : expense.paidByUser.name} paid
              </span>
              <span className="text-xs text-slate-600">·</span>
              <span className="text-xs text-slate-500">{formatDate(expense.date)}</span>
            </div>
          </div>

          <div className="flex flex-col items-end shrink-0">
            <span className="text-sm font-semibold text-slate-100">
              {formatCurrency(expense.amount, expense.currency)}
            </span>
            {balanceInfo && (
              <div
                className={cn(
                  'flex items-center gap-0.5 mt-0.5',
                  balanceInfo.type === 'lent' ? 'text-emerald-400' : 'text-red-400'
                )}
              >
                {balanceInfo.type === 'lent' ? (
                  <ArrowUpRight size={12} />
                ) : (
                  <ArrowDownLeft size={12} />
                )}
                <span className="text-xs font-medium">
                  {formatCurrency(balanceInfo.amount, expense.currency)}
                </span>
              </div>
            )}
            {isSettled && (
              <span className="text-xs text-slate-500 mt-0.5">settled</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export function ExpenseCardSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse">
      <div className="w-10 h-10 rounded-xl bg-slate-700 shrink-0" />
      <div className="flex-1">
        <div className="h-4 bg-slate-700 rounded w-2/3 mb-2" />
        <div className="h-3 bg-slate-700 rounded w-1/2" />
      </div>
      <div className="flex flex-col items-end gap-1">
        <div className="h-4 bg-slate-700 rounded w-16" />
        <div className="h-3 bg-slate-700 rounded w-12" />
      </div>
    </div>
  )
}

export function EmptyExpenses() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mb-4">
        <Receipt size={28} className="text-slate-500" />
      </div>
      <p className="text-slate-300 font-medium mb-1">No expenses yet</p>
      <p className="text-slate-500 text-sm">Add your first expense to get started</p>
    </div>
  )
}

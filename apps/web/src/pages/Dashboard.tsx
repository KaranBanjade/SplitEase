import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Users, ChevronRight, Wallet } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useGroups } from '@/hooks/useGroups'
import { useExpenses } from '@/hooks/useExpenses'
import { formatCurrency } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { ExpenseCard, ExpenseCardSkeleton } from '@/components/expenses/ExpenseCard'
import type { Expense } from '@/types'

function SummarySkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 mb-6">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="p-4 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse"
        >
          <div className="h-3 bg-slate-700 rounded w-2/3 mb-3" />
          <div className="h-6 bg-slate-700 rounded w-3/4 mb-1" />
          <div className="h-3 bg-slate-700 rounded w-1/2" />
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const { data: groups, isLoading: groupsLoading } = useGroups()
  const { data: expensesData, isLoading: expensesLoading } = useExpenses()

  const allExpenses: Expense[] = useMemo(() => {
    if (!expensesData?.pages) return []
    return expensesData.pages.flatMap((p) => p.items).slice(0, 10)
  }, [expensesData])

  const balancesByCurrency = useMemo(() => {
    if (!user || !allExpenses.length) return {}
    const owed: Record<string, number> = {}
    const owe: Record<string, number> = {}
    for (const expense of allExpenses) {
      const cur = expense.currency
      const myShare = expense.splits.find((s) => s.userId === user.id)
      if (expense.paidBy === user.id) {
        const othersOwe = expense.splits
          .filter((s) => s.userId !== user.id && !s.settledAt)
          .reduce((sum, s) => sum + s.owedAmount, 0)
        owed[cur] = (owed[cur] ?? 0) + othersOwe
      } else if (myShare && !myShare.settledAt) {
        owe[cur] = (owe[cur] ?? 0) + myShare.owedAmount
      }
    }
    const currencies = new Set([...Object.keys(owed), ...Object.keys(owe)])
    return Array.from(currencies).map((cur) => ({
      currency: cur,
      owed: owed[cur] ?? 0,
      owe: owe[cur] ?? 0,
    }))
  }, [user, allExpenses])

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="px-4 pt-4 pb-6 max-w-lg mx-auto space-y-6">
      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <p className="text-slate-400 text-sm">{greeting()},</p>
        <h2 className="text-xl font-bold text-slate-100">
          {user?.name?.split(' ')[0] ?? 'there'} 👋
        </h2>
      </motion.div>

      {/* Summary Cards */}
      {expensesLoading ? (
        <SummarySkeleton />
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 gap-3"
        >
          <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-600/20 to-emerald-800/10 border border-emerald-500/20">
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp size={14} className="text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">
                You are owed
              </span>
            </div>
            {Array.isArray(balancesByCurrency) && balancesByCurrency.some((b) => b.owed > 0) ? (
              balancesByCurrency.filter((b) => b.owed > 0).map((b) => (
                <p key={b.currency} className="text-xl font-bold text-emerald-400 leading-tight">
                  {formatCurrency(b.owed, b.currency)}
                </p>
              ))
            ) : (
              <p className="text-xl font-bold text-emerald-400">
                {formatCurrency(0)}
              </p>
            )}
            <p className="text-xs text-slate-500 mt-0.5">across all groups</p>
          </div>

          <div className="p-4 rounded-2xl bg-gradient-to-br from-red-600/20 to-red-800/10 border border-red-500/20">
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingDown size={14} className="text-red-400" />
              <span className="text-xs text-red-400 font-medium">You owe</span>
            </div>
            {Array.isArray(balancesByCurrency) && balancesByCurrency.some((b) => b.owe > 0) ? (
              balancesByCurrency.filter((b) => b.owe > 0).map((b) => (
                <p key={b.currency} className="text-xl font-bold text-red-400 leading-tight">
                  {formatCurrency(b.owe, b.currency)}
                </p>
              ))
            ) : (
              <p className="text-xl font-bold text-red-400">
                {formatCurrency(0)}
              </p>
            )}
            <p className="text-xs text-slate-500 mt-0.5">to others</p>
          </div>
        </motion.div>
      )}

      {/* Active Groups */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            Your Groups
          </h3>
          <Link
            to="/groups"
            className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
          >
            See all
          </Link>
        </div>

        {groupsLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse"
              >
                <div className="w-10 h-10 rounded-xl bg-slate-700" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-slate-700 rounded w-1/2" />
                  <div className="h-3 bg-slate-700 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : !groups?.length ? (
          <Card className="text-center py-8">
            <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center mx-auto mb-3">
              <Users size={22} className="text-slate-500" />
            </div>
            <p className="text-slate-400 text-sm mb-1">No groups yet</p>
            <Link
              to="/groups"
              className="text-primary-400 text-sm hover:text-primary-300"
            >
              Create your first group
            </Link>
          </Card>
        ) : (
          <div className="space-y-2">
            {groups.slice(0, 3).map((group) => (
              <Link key={group.id} to={`/groups/${group.id}`}>
                <Card
                  onClick={() => {}}
                  className="flex items-center gap-3 !p-3"
                >
                  <div className="w-10 h-10 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center shrink-0">
                    <span className="text-primary-400 font-bold text-sm">
                      {group.name[0].toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-100 truncate">
                      {group.name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {group.members.length} member
                      {group.members.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge color="purple">{group.currency}</Badge>
                    <ChevronRight size={16} className="text-slate-600" />
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Recent Expenses */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            Recent Expenses
          </h3>
        </div>

        {expensesLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <ExpenseCardSkeleton key={i} />
            ))}
          </div>
        ) : !allExpenses.length ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mb-3">
              <Wallet size={22} className="text-slate-500" />
            </div>
            <p className="text-slate-400 text-sm">No recent expenses</p>
          </div>
        ) : (
          <div className="space-y-2">
            {allExpenses.map((expense) => (
              <ExpenseCard key={expense.id} expense={expense} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

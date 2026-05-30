import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeftRight, Wallet } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useExpenses } from '@/hooks/useExpenses'
import { useGroups } from '@/hooks/useGroups'
import { ExpenseCard, ExpenseCardSkeleton } from '@/components/expenses/ExpenseCard'
import type { Expense } from '@/types'

export default function Activity() {
  const user = useAuthStore((s) => s.user)
  const { data: groups } = useGroups()
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useExpenses()

  const allExpenses: Expense[] = useMemo(() => {
    if (!data?.pages) return []
    return data.pages.flatMap((p) => p.items)
  }, [data])

  const groupMap = useMemo(() => {
    const map: Record<string, string> = {}
    groups?.forEach((g) => { map[g.id] = g.name })
    return map
  }, [groups])

  return (
    <div className="px-4 pt-4 pb-6 max-w-lg mx-auto">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center gap-2 mb-5"
      >
        <div className="w-8 h-8 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center">
          <ArrowLeftRight size={16} className="text-primary-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-100">Activity</h2>
          <p className="text-xs text-slate-500">All recent expenses across your groups</p>
        </div>
      </motion.div>

      <div className="space-y-2">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => <ExpenseCardSkeleton key={i} />)
        ) : allExpenses.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center mb-4">
              <Wallet size={24} className="text-slate-500" />
            </div>
            <p className="text-slate-300 font-medium mb-1">No activity yet</p>
            <p className="text-slate-500 text-sm">
              Add your first expense to a group to see it here.
            </p>
          </div>
        ) : (
          <>
            {allExpenses.map((expense) => (
              <div key={expense.id}>
                {groupMap[expense.groupId] && (
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium px-1 mb-1 mt-3 first:mt-0">
                    {groupMap[expense.groupId]}
                  </p>
                )}
                <ExpenseCard expense={expense} currentUserId={user?.id} />
              </div>
            ))}

            {hasNextPage && (
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="w-full py-3 text-sm text-primary-400 hover:text-primary-300 disabled:opacity-50 transition-colors"
              >
                {isFetchingNextPage ? 'Loading…' : 'Load more'}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

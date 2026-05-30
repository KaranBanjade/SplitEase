import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ChevronLeft, Bell, SplitSquareHorizontal, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn, formatRelativeTime, formatCurrency } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { useExpenses } from '@/hooks/useExpenses'
import type { Expense } from '@/types'

const ROOT_ROUTES = ['/', '/groups', '/activity', '/profile']

function NotificationPanel({ onClose }: { onClose: () => void }) {
  const user = useAuthStore((s) => s.user)
  const { data, isLoading } = useExpenses()
  const panelRef = useRef<HTMLDivElement>(null)

  const recent: Expense[] = useMemo(() => {
    if (!data?.pages) return []
    return data.pages.flatMap((p) => p.items).slice(0, 8)
  }, [data])

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  return (
    <motion.div
      ref={panelRef}
      initial={{ opacity: 0, y: -8, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.97 }}
      transition={{ duration: 0.15 }}
      className="absolute right-2 top-full mt-2 w-80 bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden z-50"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <span className="text-sm font-semibold text-slate-100">Recent Activity</span>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
        >
          <X size={15} />
        </button>
      </div>

      <div className="max-h-80 overflow-y-auto overscroll-contain">
        {isLoading ? (
          <div className="space-y-0">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3 animate-pulse">
                <div className="w-8 h-8 rounded-xl bg-slate-700 shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 bg-slate-700 rounded w-3/4" />
                  <div className="h-2.5 bg-slate-700 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-500">
            No activity yet
          </div>
        ) : (
          recent.map((expense) => {
            const isMyExpense = expense.paidBy === user?.id
            const myShare = expense.splits.find((s) => s.userId === user?.id)
            const owedAmount = myShare?.owedAmount ?? 0

            return (
              <div
                key={expense.id}
                className="flex items-start gap-3 px-4 py-3 hover:bg-slate-700/50 transition-colors border-b border-slate-700/50 last:border-0"
              >
                <div className="w-8 h-8 rounded-xl bg-primary-600/20 border border-primary-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-primary-400">
                    {expense.description[0].toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 font-medium truncate">
                    {expense.description}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {isMyExpense
                      ? `You paid ${formatCurrency(Number(expense.amount), expense.currency)}`
                      : `${expense.paidByUser?.name ?? 'Someone'} paid · you owe ${formatCurrency(owedAmount, expense.currency)}`}
                  </p>
                </div>
                <span className="text-[10px] text-slate-500 shrink-0 mt-0.5">
                  {formatRelativeTime(expense.createdAt)}
                </span>
              </div>
            )
          })
        )}
      </div>
    </motion.div>
  )
}

export function Header() {
  const navigate = useNavigate()
  const location = useLocation()
  const [notifOpen, setNotifOpen] = useState(false)

  const isRoot = ROOT_ROUTES.includes(location.pathname)
  const canGoBack = !isRoot

  // Close panel on route change
  useEffect(() => { setNotifOpen(false) }, [location.pathname])

  const getTitle = () => {
    const { pathname } = location
    if (pathname === '/') return 'SplitEase'
    if (pathname === '/groups') return 'Groups'
    if (pathname === '/activity') return 'Activity'
    if (pathname === '/profile') return 'Profile'
    if (pathname.endsWith('/add-expense')) return 'Add Expense'
    if (pathname.endsWith('/settlements')) return 'Settlements'
    if (pathname.includes('/groups/')) return 'Group'
    return 'SplitEase'
  }

  return (
    <header className="sticky top-0 z-30 safe-top bg-slate-900/95 backdrop-blur-md border-b border-slate-800">
      <div className="flex items-center justify-between h-14 px-4 max-w-lg mx-auto">
        <div className="flex items-center gap-2 min-w-0">
          {canGoBack ? (
            <button
              onClick={() => navigate(-1)}
              className="p-1.5 -ml-1.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <ChevronLeft size={22} />
            </button>
          ) : (
            <div className="w-7 h-7 rounded-lg bg-primary-600 flex items-center justify-center">
              <SplitSquareHorizontal size={16} className="text-white" />
            </div>
          )}
          <h1 className={cn('font-semibold text-slate-100 truncate', canGoBack ? 'text-base' : 'text-lg')}>
            {getTitle()}
          </h1>
        </div>

        {/* Notification bell */}
        <div className="relative">
          <button
            onClick={() => setNotifOpen((v) => !v)}
            className={cn(
              'p-2 rounded-xl transition-colors relative',
              notifOpen
                ? 'text-primary-400 bg-primary-500/10'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800',
            )}
          >
            <Bell size={20} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-primary-500" />
          </button>

          <AnimatePresence>
            {notifOpen && <NotificationPanel onClose={() => setNotifOpen(false)} />}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}

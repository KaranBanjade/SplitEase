import { useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Users, UserPlus, Receipt, BarChart3, ArrowLeftRight, ChevronDown, ChevronUp } from 'lucide-react'
import { useGroup, useGroupBalances, useSimplifiedDebts, useInviteMember } from '@/hooks/useGroups'
import { useExpenses } from '@/hooks/useExpenses'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { ExpenseCard, ExpenseCardSkeleton, EmptyExpenses } from '@/components/expenses/ExpenseCard'
import { BalanceCard, BalanceCardSkeleton } from '@/components/expenses/BalanceCard'
import { DebtSimplificationView } from '@/components/expenses/DebtSimplificationView'
import { cn } from '@/lib/utils'

type Tab = 'expenses' | 'balances' | 'debts'

const inviteSchema = z.object({
  email: z.string().email('Invalid email'),
})

export default function GroupDetail() {
  const { id } = useParams<{ id: string }>()
  const groupId = id!

  const [activeTab, setActiveTab] = useState<Tab>('expenses')
  const [membersExpanded, setMembersExpanded] = useState(false)
  const [inviteModalOpen, setInviteModalOpen] = useState(false)

  const { data: group, isLoading: groupLoading } = useGroup(groupId)
  const { data: balances, isLoading: balancesLoading } = useGroupBalances(groupId)
  const { data: debts, isLoading: debtsLoading } = useSimplifiedDebts(groupId)
  const {
    data: expensesData,
    isLoading: expensesLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useExpenses(groupId)
  const { mutate: inviteMember, isPending: inviting } = useInviteMember()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<{ email: string }>({
    resolver: zodResolver(inviteSchema),
  })

  const allExpenses = expensesData?.pages.flatMap((p) => p.items) ?? []

  const handleInvite = (data: { email: string }) => {
    inviteMember(
      { groupId, email: data.email },
      {
        onSuccess: () => {
          setInviteModalOpen(false)
          reset()
        },
      }
    )
  }

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
      if (nearBottom && hasNextPage && !isFetchingNextPage) {
        fetchNextPage()
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage]
  )

  if (groupLoading) {
    return (
      <div className="px-4 pt-4 max-w-lg mx-auto animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/2 mb-2" />
        <div className="h-4 bg-slate-700 rounded w-1/3 mb-6" />
        <div className="h-10 bg-slate-700 rounded-xl mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <ExpenseCardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  if (!group) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center px-4">
        <p className="text-slate-300 font-medium">Group not found</p>
        <Link to="/groups" className="text-primary-400 text-sm mt-2">
          Back to groups
        </Link>
      </div>
    )
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'expenses', label: 'Expenses', icon: <Receipt size={14} /> },
    { id: 'balances', label: 'Balances', icon: <BarChart3 size={14} /> },
    { id: 'debts', label: 'Debts', icon: <ArrowLeftRight size={14} /> },
  ]

  return (
    <div className="max-w-lg mx-auto" onScroll={handleScroll}>
      {/* Group Info */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-600/30 to-primary-800/20 border border-primary-500/30 flex items-center justify-center">
              <span className="text-primary-400 font-bold text-2xl">
                {group.name[0].toUpperCase()}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100">{group.name}</h2>
              {group.description && (
                <p className="text-sm text-slate-400">{group.description}</p>
              )}
              <Badge color="purple" className="mt-1">
                {group.currency}
              </Badge>
            </div>
          </div>
          <Link to={`/groups/${groupId}/add-expense`}>
            <Button size="sm" className="gap-1">
              <Plus size={14} />
              Add
            </Button>
          </Link>
        </div>

        {/* Members */}
        <div className="bg-slate-800/60 rounded-2xl border border-slate-700/50 overflow-hidden">
          <button
            className="w-full flex items-center justify-between px-4 py-3"
            onClick={() => setMembersExpanded((v) => !v)}
          >
            <div className="flex items-center gap-2">
              <Users size={15} className="text-slate-400" />
              <span className="text-sm font-medium text-slate-300">
                {group.members.length} member
                {group.members.length !== 1 ? 's' : ''}
              </span>
              <div className="flex -space-x-1">
                {group.members.slice(0, 4).map((m) => (
                  <Avatar key={m.userId} name={m.user.name} size="xs" />
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setInviteModalOpen(true)
                }}
                className="p-1 rounded-lg bg-primary-600/20 text-primary-400 hover:bg-primary-600/30 transition-colors"
              >
                <UserPlus size={14} />
              </button>
              {membersExpanded ? (
                <ChevronUp size={16} className="text-slate-500" />
              ) : (
                <ChevronDown size={16} className="text-slate-500" />
              )}
            </div>
          </button>

          <AnimatePresence>
            {membersExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-3 space-y-2 border-t border-slate-700/50 pt-2">
                  {group.members.map((member) => (
                    <div
                      key={member.userId}
                      className="flex items-center gap-2"
                    >
                      <Avatar
                        name={member.user.name}
                        src={member.user.avatarUrl}
                        size="sm"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-200 truncate">
                          {member.user.name}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                          {member.user.email}
                        </p>
                      </div>
                      {member.role === 'owner' && (
                        <Badge color="purple">Owner</Badge>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="sticky top-14 z-20 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800 px-4">
        <div className="flex gap-1 py-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-sm font-medium transition-all',
                activeTab === tab.id
                  ? 'bg-primary-600 text-white shadow-lg shadow-primary-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="px-4 py-4">
        <AnimatePresence mode="wait">
          {activeTab === 'expenses' && (
            <motion.div
              key="expenses"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-2"
            >
              {expensesLoading ? (
                [1, 2, 3].map((i) => <ExpenseCardSkeleton key={i} />)
              ) : !allExpenses.length ? (
                <EmptyExpenses />
              ) : (
                <>
                  {allExpenses.map((expense) => (
                    <ExpenseCard key={expense.id} expense={expense} />
                  ))}
                  {hasNextPage && (
                    <div className="flex justify-center pt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={isFetchingNextPage}
                        onClick={() => fetchNextPage()}
                      >
                        Load more
                      </Button>
                    </div>
                  )}
                </>
              )}
            </motion.div>
          )}

          {activeTab === 'balances' && (
            <motion.div
              key="balances"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-2"
            >
              {balancesLoading ? (
                [1, 2, 3].map((i) => <BalanceCardSkeleton key={i} />)
              ) : !balances?.length ? (
                <div className="text-center py-12 text-slate-400 text-sm">
                  No balance data available
                </div>
              ) : (
                balances.map((balance) => (
                  <BalanceCard
                    key={balance.userId}
                    balance={balance}
                    currency={group.currency}
                  />
                ))
              )}
            </motion.div>
          )}

          {activeTab === 'debts' && (
            <motion.div
              key="debts"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
            >
              <DebtSimplificationView
                debts={debts ?? []}
                groupId={groupId}
                isLoading={debtsLoading}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Invite Member Modal */}
      <Modal
        isOpen={inviteModalOpen}
        onClose={() => {
          setInviteModalOpen(false)
          reset()
        }}
        title="Invite Member"
      >
        <form
          onSubmit={handleSubmit(handleInvite)}
          className="p-4 space-y-4"
        >
          <Input
            label="Email address"
            type="email"
            placeholder="friend@example.com"
            error={errors.email?.message}
            {...register('email')}
          />
          <div className="flex gap-3">
            <Button
              type="button"
              variant="secondary"
              fullWidth
              onClick={() => {
                setInviteModalOpen(false)
                reset()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" fullWidth loading={inviting}>
              Invite
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

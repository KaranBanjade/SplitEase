import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Plus, ArrowRight, Receipt } from 'lucide-react'
import { useGroup } from '@/hooks/useGroups'
import { useSettlements, useCreateSettlement } from '@/hooks/useSettlements'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Avatar } from '@/components/ui/Avatar'
import { formatCurrency, formatDate, cn, CURRENCIES } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'

const settlementSchema = z.object({
  paidBy: z.string().min(1, 'Select who paid'),
  paidTo: z.string().min(1, 'Select who received'),
  amount: z.number().min(0.01, 'Amount must be positive'),
  currency: z.string(),
  notes: z.string().max(200).optional(),
})

type SettlementForm = z.infer<typeof settlementSchema>

function SettlementSkeleton() {
  return (
    <div className="flex items-center gap-3 p-4 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse">
      <div className="w-8 h-8 rounded-full bg-slate-700" />
      <div className="w-8 h-4 bg-slate-700 rounded" />
      <div className="w-8 h-8 rounded-full bg-slate-700" />
      <div className="flex-1 space-y-2 ml-2">
        <div className="h-4 bg-slate-700 rounded w-2/3" />
        <div className="h-3 bg-slate-700 rounded w-1/3" />
      </div>
      <div className="h-5 bg-slate-700 rounded w-16" />
    </div>
  )
}

export default function Settlements() {
  const { id: groupId } = useParams<{ id: string }>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const currentUser = useAuthStore((s) => s.user)

  const { data: group } = useGroup(groupId!)
  const { data: settlements, isLoading } = useSettlements(groupId!)
  const { mutate: createSettlement, isPending } = useCreateSettlement()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<SettlementForm>({
    resolver: zodResolver(settlementSchema),
    defaultValues: {
      currency: group?.currency ?? 'INR',
      paidBy: currentUser?.id ?? '',
    },
  })

  const [paidBy, paidTo] = watch(['paidBy', 'paidTo'])

  const onSubmit = (data: SettlementForm) => {
    createSettlement(
      {
        groupId: groupId!,
        paidBy: data.paidBy,
        paidTo: data.paidTo,
        amount: data.amount,
        currency: data.currency,
        notes: data.notes,
      },
      {
        onSuccess: () => {
          setIsModalOpen(false)
          reset()
        },
      }
    )
  }

  return (
    <div className="px-4 pt-4 pb-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Settlements</h2>
          <p className="text-sm text-slate-400">
            {settlements?.length ?? 0} recorded
          </p>
        </div>
        <Button size="sm" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} />
          Record
        </Button>
      </div>

      {/* Settlements List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <SettlementSkeleton key={i} />
          ))}
        </div>
      ) : !settlements?.length ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-16 text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mb-4">
            <Receipt size={28} className="text-slate-500" />
          </div>
          <p className="text-slate-300 font-medium mb-1">No settlements yet</p>
          <p className="text-slate-500 text-sm">
            Record a payment when someone settles up
          </p>
        </motion.div>
      ) : (
        <div className="space-y-3">
          {settlements.map((settlement, index) => {
            const isMyPayment = settlement.paidBy === currentUser?.id
            const isOwedToMe = settlement.paidTo === currentUser?.id

            return (
              <motion.div
                key={settlement.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
                className={cn(
                  'flex items-center gap-3 p-4 rounded-2xl border',
                  isMyPayment
                    ? 'bg-emerald-500/5 border-emerald-500/20'
                    : isOwedToMe
                    ? 'bg-blue-500/5 border-blue-500/20'
                    : 'bg-slate-800 border-slate-700/50'
                )}
              >
                <Avatar
                  name={settlement.paidByUser.name}
                  src={settlement.paidByUser.avatarUrl}
                  size="sm"
                />
                <ArrowRight size={14} className="text-emerald-400 shrink-0" />
                <Avatar
                  name={settlement.paidToUser.name}
                  src={settlement.paidToUser.avatarUrl}
                  size="sm"
                />

                <div className="flex-1 min-w-0 ml-1">
                  <p className="text-sm font-medium text-slate-100">
                    {isMyPayment ? 'You' : settlement.paidByUser.name}{' '}
                    <span className="text-slate-400">paid</span>{' '}
                    {isOwedToMe ? 'you' : settlement.paidToUser.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatDate(settlement.createdAt)}
                    {settlement.notes && ` · ${settlement.notes}`}
                  </p>
                </div>

                <span className="text-sm font-semibold text-emerald-400 shrink-0">
                  {formatCurrency(settlement.amount, settlement.currency)}
                </span>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* Record Settlement Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          reset()
        }}
        title="Record Settlement"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="p-4 space-y-4">
          {/* Who Paid */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Who paid</label>
            <div className="flex flex-wrap gap-2">
              {group?.members.map((member) => (
                <button
                  key={member.userId}
                  type="button"
                  onClick={() => setValue('paidBy', member.userId)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition-all',
                    paidBy === member.userId
                      ? 'bg-primary-600/20 border-primary-500 text-primary-300'
                      : 'bg-slate-800/60 border-slate-700 text-slate-400'
                  )}
                >
                  <Avatar name={member.user.name} size="xs" />
                  {member.userId === currentUser?.id
                    ? 'You'
                    : member.user.name}
                </button>
              ))}
            </div>
            {errors.paidBy && (
              <p className="text-xs text-red-400">{errors.paidBy.message}</p>
            )}
          </div>

          {/* Who Received */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Paid to</label>
            <div className="flex flex-wrap gap-2">
              {group?.members
                .filter((m) => m.userId !== paidBy)
                .map((member) => (
                  <button
                    key={member.userId}
                    type="button"
                    onClick={() => setValue('paidTo', member.userId)}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition-all',
                      paidTo === member.userId
                        ? 'bg-primary-600/20 border-primary-500 text-primary-300'
                        : 'bg-slate-800/60 border-slate-700 text-slate-400'
                    )}
                  >
                    <Avatar name={member.user.name} size="xs" />
                    {member.userId === currentUser?.id
                      ? 'You'
                      : member.user.name}
                  </button>
                ))}
            </div>
            {errors.paidTo && (
              <p className="text-xs text-red-400">{errors.paidTo.message}</p>
            )}
          </div>

          {/* Amount */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <Input
                label="Amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                error={errors.amount?.message}
                {...register('amount', { valueAsNumber: true })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-slate-300">
                Currency
              </label>
              <select
                className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100 px-3 py-2.5 text-sm outline-none focus:border-primary-500"
                {...register('currency')}
              >
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes */}
          <Input
            label="Notes (optional)"
            placeholder="Venmo, cash, etc."
            {...register('notes')}
          />

          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              fullWidth
              onClick={() => {
                setIsModalOpen(false)
                reset()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" fullWidth loading={isPending}>
              Record
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

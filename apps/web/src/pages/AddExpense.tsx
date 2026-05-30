import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import {
  DollarSign,
  Calendar,
  Tag,
  UserCircle,
  SplitSquareHorizontal,
  RefreshCw,
} from 'lucide-react'
import { useGroup } from '@/hooks/useGroups'
import { useCreateExpense } from '@/hooks/useExpenses'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Avatar } from '@/components/ui/Avatar'
import { CATEGORIES, CURRENCIES, formatCurrency, cn } from '@/lib/utils'
import type { SplitType, RecurringFrequency } from '@/types'
import { format } from 'date-fns'

const splitItemSchema = z.object({
  userId: z.string(),
  shareAmount: z.number().min(0),
  owedAmount: z.number().min(0),
})

const addExpenseSchema = z.object({
  description: z.string().min(1, 'Description is required').max(200),
  amount: z.number().min(0.01, 'Amount must be positive'),
  currency: z.string(),
  paidBy: z.string().min(1, 'Please select who paid'),
  category: z.string().min(1, 'Please select a category'),
  date: z.string().min(1, 'Please select a date'),
  splitType: z.enum(['equal', 'exact', 'percentage']),
  splits: z.array(splitItemSchema),
  isRecurring: z.boolean(),
  frequency: z.enum(['daily', 'weekly', 'monthly', 'yearly']).optional(),
})

type AddExpenseForm = z.infer<typeof addExpenseSchema>

export default function AddExpense() {
  const { id: groupId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const currentUser = useAuthStore((s) => s.user)
  const { data: group } = useGroup(groupId!)
  const { mutate: createExpense, isPending } = useCreateExpense()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    formState: { errors },
  } = useForm<AddExpenseForm>({
    resolver: zodResolver(addExpenseSchema),
    defaultValues: {
      date: format(new Date(), 'yyyy-MM-dd'),
      currency: group?.currency ?? 'INR',
      paidBy: currentUser?.id ?? '',
      splitType: 'equal',
      isRecurring: false,
      splits: [],
      category: 'Food',
    },
  })

  const { fields, replace } = useFieldArray({ control, name: 'splits' })

  const [splitType, amount, isRecurring, paidBy, currency] = watch([
    'splitType',
    'amount',
    'isRecurring',
    'paidBy',
    'currency',
  ])

  // Initialize splits when group loads
  useEffect(() => {
    if (group?.members) {
      replace(
        group.members.map((m) => ({
          userId: m.userId,
          shareAmount: 0,
          owedAmount: 0,
        }))
      )
    }
  }, [group?.members, replace])

  // Compute equal splits
  useEffect(() => {
    if (splitType === 'equal' && group?.members && amount > 0) {
      const share = amount / group.members.length
      replace(
        group.members.map((m) => ({
          userId: m.userId,
          shareAmount: share,
          owedAmount: m.userId === paidBy ? 0 : share,
        }))
      )
    }
  }, [splitType, amount, group?.members, paidBy, replace])

  const onSubmit = (data: AddExpenseForm) => {
    createExpense(
      {
        groupId: groupId!,
        description: data.description,
        amount: data.amount,
        currency: data.currency,
        paidBy: data.paidBy,
        category: data.category,
        date: data.date,
        splitType: data.splitType as SplitType,
        splits: data.splits,
        isRecurring: data.isRecurring,
        ...(data.isRecurring && data.frequency ? { frequency: data.frequency as RecurringFrequency } : {}),
      },
      {
        onSuccess: () => navigate(`/groups/${groupId}`),
      }
    )
  }

  const totalSplit = fields.reduce((sum, _, i) => {
    const v = watch(`splits.${i}.owedAmount`)
    return sum + (Number(v) || 0)
  }, 0)

  const splitValid =
    splitType === 'equal' || Math.abs(totalSplit - (Number(amount) || 0)) < 0.01

  if (!group) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 pt-4 pb-8">
      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5"
      >
        {/* Description */}
        <Input
          label="Description"
          placeholder="Dinner, groceries, Netflix..."
          error={errors.description?.message}
          {...register('description')}
        />

        {/* Amount + Currency */}
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Input
              label="Amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              leftIcon={<DollarSign size={16} />}
              error={errors.amount?.message}
              {...register('amount', { valueAsNumber: true })}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Currency</label>
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

        {/* Category + Date */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">
              Category
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <Tag size={14} />
              </span>
              <select
                className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100 pl-9 pr-3 py-2.5 text-sm outline-none focus:border-primary-500 appearance-none"
                {...register('category')}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Date</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <Calendar size={14} />
              </span>
              <input
                type="date"
                className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100 pl-9 pr-3 py-2.5 text-sm outline-none focus:border-primary-500 [color-scheme:dark]"
                {...register('date')}
              />
            </div>
          </div>
        </div>

        {/* Paid By */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-slate-300">
            Paid by
          </label>
          <div className="flex gap-2 flex-wrap">
            {group.members.map((member) => {
              const isSelected = paidBy === member.userId
              return (
                <button
                  key={member.userId}
                  type="button"
                  onClick={() => setValue('paidBy', member.userId)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium transition-all',
                    isSelected
                      ? 'bg-primary-600/20 border-primary-500 text-primary-300'
                      : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                  )}
                >
                  <Avatar
                    name={member.user.name}
                    src={member.user.avatarUrl}
                    size="xs"
                  />
                  {member.userId === currentUser?.id
                    ? 'You'
                    : member.user.name}
                </button>
              )
            })}
          </div>
          {errors.paidBy && (
            <p className="text-xs text-red-400">{errors.paidBy.message}</p>
          )}
        </div>

        {/* Split Type */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-slate-300">
            Split type
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['equal', 'exact', 'percentage'] as SplitType[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setValue('splitType', type)}
                className={cn(
                  'flex items-center justify-center gap-1.5 py-2.5 rounded-xl border text-sm font-medium transition-all',
                  splitType === type
                    ? 'bg-primary-600/20 border-primary-500 text-primary-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                )}
              >
                <SplitSquareHorizontal size={14} />
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Split Inputs (for exact/percentage) */}
        {(splitType === 'exact' || splitType === 'percentage') && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-slate-300">
                Split amounts
              </label>
              <span
                className={cn(
                  'text-xs font-medium',
                  splitValid ? 'text-emerald-400' : 'text-red-400'
                )}
              >
                {splitType === 'percentage'
                  ? `${fields.reduce((s, _, i) => s + (Number(watch(`splits.${i}.shareAmount`)) || 0), 0).toFixed(0)}%`
                  : `${formatCurrency(totalSplit, currency)} / ${formatCurrency(Number(amount) || 0, currency)}`}
              </span>
            </div>
            {fields.map((field, index) => {
              const member = group.members.find((m) => m.userId === field.userId)
              if (!member) return null
              return (
                <div
                  key={field.id}
                  className="flex items-center gap-3 bg-slate-800 rounded-xl p-3 border border-slate-700/50"
                >
                  <Avatar
                    name={member.user.name}
                    src={member.user.avatarUrl}
                    size="sm"
                  />
                  <span className="flex-1 text-sm text-slate-300 truncate">
                    {member.userId === currentUser?.id
                      ? 'You'
                      : member.user.name}
                  </span>
                  <div className="w-28">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      className="w-full rounded-lg bg-slate-700 border border-slate-600 text-slate-100 px-3 py-1.5 text-sm outline-none focus:border-primary-500 text-right"
                      {...register(`splits.${index}.owedAmount`, {
                        valueAsNumber: true,
                        onChange: (e) => {
                          const val = parseFloat(e.target.value) || 0
                          setValue(`splits.${index}.shareAmount`, val)
                        },
                      })}
                    />
                  </div>
                  <span className="text-xs text-slate-500">
                    {splitType === 'percentage' ? '%' : currency}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* Equal split preview */}
        {splitType === 'equal' && amount > 0 && group.members.length > 0 && (
          <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/50">
            <p className="text-xs text-slate-400 mb-2">Each person pays:</p>
            <p className="text-lg font-bold text-slate-100">
              {formatCurrency(amount / group.members.length, currency)}
            </p>
          </div>
        )}

        {/* Recurring */}
        <div className="flex flex-col gap-3">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-2">
              <RefreshCw size={16} className="text-slate-400" />
              <span className="text-sm font-medium text-slate-300">
                Recurring expense
              </span>
            </div>
            <div
              onClick={() => setValue('isRecurring', !isRecurring)}
              className={cn(
                'relative w-11 h-6 rounded-full transition-colors cursor-pointer',
                isRecurring ? 'bg-primary-600' : 'bg-slate-700'
              )}
            >
              <div
                className={cn(
                  'absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform shadow',
                  isRecurring && 'translate-x-5'
                )}
              />
            </div>
          </label>

          {isRecurring && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
            >
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-300">
                  Frequency
                </label>
                <select
                  className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100 px-3.5 py-2.5 text-sm outline-none focus:border-primary-500"
                  {...register('frequency')}
                >
                  {(['daily', 'weekly', 'monthly', 'yearly'] as RecurringFrequency[]).map(
                    (f) => (
                      <option key={f} value={f}>
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                      </option>
                    )
                  )}
                </select>
              </div>
            </motion.div>
          )}
        </div>

        {/* Submit */}
        <div className="flex gap-3 pt-2">
          <Button
            type="button"
            variant="secondary"
            fullWidth
            onClick={() => navigate(-1)}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            fullWidth
            loading={isPending}
            disabled={splitType !== 'equal' && !splitValid}
          >
            Add Expense
          </Button>
        </div>
      </motion.form>
    </div>
  )
}

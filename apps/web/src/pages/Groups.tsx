import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Plus, Users, ChevronRight, DollarSign } from 'lucide-react'
import { useGroups, useCreateGroup } from '@/hooks/useGroups'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { CURRENCIES } from '@/lib/utils'

const createGroupSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(50),
  description: z.string().max(200).optional(),
  currency: z.string().min(1, 'Please select a currency'),
})

type CreateGroupForm = z.infer<typeof createGroupSchema>

function GroupSkeleton() {
  return (
    <div className="flex items-center gap-3 p-4 rounded-2xl bg-slate-800 border border-slate-700/50 animate-pulse">
      <div className="w-12 h-12 rounded-xl bg-slate-700 shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-slate-700 rounded w-1/2" />
        <div className="h-3 bg-slate-700 rounded w-1/3" />
      </div>
      <div className="w-12 h-6 bg-slate-700 rounded-full" />
    </div>
  )
}

export default function Groups() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { data: groups, isLoading } = useGroups()
  const { mutate: createGroup, isPending } = useCreateGroup()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateGroupForm>({
    resolver: zodResolver(createGroupSchema),
    defaultValues: { currency: 'INR' },
  })

  const onSubmit = (data: CreateGroupForm) => {
    createGroup(data, {
      onSuccess: () => {
        setIsModalOpen(false)
        reset()
      },
    })
  }

  return (
    <div className="px-4 pt-4 pb-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Groups</h2>
          <p className="text-sm text-slate-400">
            {groups?.length ?? 0} group{(groups?.length ?? 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setIsModalOpen(true)}
          className="gap-1"
        >
          <Plus size={16} />
          New Group
        </Button>
      </div>

      {/* Groups list */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <GroupSkeleton key={i} />
          ))}
        </div>
      ) : !groups?.length ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 text-center px-4"
        >
          <div className="w-20 h-20 rounded-3xl bg-slate-800 flex items-center justify-center mb-5 shadow-xl">
            <Users size={34} className="text-slate-500" />
          </div>
          <h3 className="text-lg font-semibold text-slate-200 mb-2">
            No groups yet
          </h3>
          <p className="text-slate-400 text-sm mb-6 max-w-xs">
            Create a group to start tracking shared expenses with friends,
            family, or roommates.
          </p>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus size={16} />
            Create first group
          </Button>
        </motion.div>
      ) : (
        <div className="space-y-3">
          {groups.map((group, index) => (
            <motion.div
              key={group.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Link to={`/groups/${group.id}`}>
                <Card onClick={() => {}} padding="none">
                  <div className="flex items-center gap-3 p-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600/30 to-primary-800/20 border border-primary-500/30 flex items-center justify-center shrink-0">
                      <span className="text-primary-400 font-bold text-lg">
                        {group.name[0].toUpperCase()}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-slate-100 truncate">
                        {group.name}
                      </p>
                      {group.description && (
                        <p className="text-xs text-slate-500 truncate mt-0.5">
                          {group.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-slate-500">
                          {group.members.length} member
                          {group.members.length !== 1 ? 's' : ''}
                        </span>
                        <span className="text-slate-700">·</span>
                        <div className="flex -space-x-1">
                          {group.members.slice(0, 3).map((m) => (
                            <div
                              key={m.userId}
                              className="w-4 h-4 rounded-full bg-slate-600 border border-slate-800 flex items-center justify-center text-[8px] text-white font-bold"
                            >
                              {m.user.name[0].toUpperCase()}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge color="purple">{group.currency}</Badge>
                      <ChevronRight size={16} className="text-slate-600" />
                    </div>
                  </div>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      )}

      {/* Create Group Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          reset()
        }}
        title="Create Group"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="p-4 space-y-4">
          <Input
            label="Group name"
            placeholder="Trip to Paris, Apartment..."
            error={errors.name?.message}
            {...register('name')}
          />

          <Input
            label="Description (optional)"
            placeholder="What's this group for?"
            error={errors.description?.message}
            {...register('description')}
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">
              Currency
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <DollarSign size={16} />
              </span>
              <select
                className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100 pl-10 pr-3.5 py-2.5 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 appearance-none"
                {...register('currency')}
              >
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code} — {c.label}
                  </option>
                ))}
              </select>
            </div>
            {errors.currency && (
              <p className="text-xs text-red-400">{errors.currency.message}</p>
            )}
          </div>

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
              Create Group
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Bell, LogOut, Edit2, Check, X } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useLogout, useUpdateProfile } from '@/hooks/useAuth'
import { Avatar } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import {
  requestPermission,
  subscribeToPush,
  isPushSubscribed,
  unsubscribeFromPush,
} from '@/lib/pushNotifications'
import { formatDate } from '@/lib/utils'
import toast from 'react-hot-toast'

const profileSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(50),
})

type ProfileForm = z.infer<typeof profileSchema>

export default function Profile() {
  const user = useAuthStore((s) => s.user)
  const [isEditing, setIsEditing] = useState(false)
  const [pushEnabled, setPushEnabled] = useState(false)
  const [pushLoading, setPushLoading] = useState(false)

  const { mutate: logout, isPending: loggingOut } = useLogout()
  const { mutate: updateProfile, isPending: updating } = useUpdateProfile()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: { name: user?.name ?? '' },
  })

  useEffect(() => {
    isPushSubscribed().then(setPushEnabled)
  }, [])

  const onSave = (data: ProfileForm) => {
    updateProfile(
      { name: data.name },
      {
        onSuccess: () => setIsEditing(false),
      }
    )
  }

  const handleCancel = () => {
    setIsEditing(false)
    reset({ name: user?.name ?? '' })
  }

  const handlePushToggle = async () => {
    setPushLoading(true)
    try {
      if (pushEnabled) {
        const success = await unsubscribeFromPush()
        if (success) {
          setPushEnabled(false)
          toast.success('Push notifications disabled')
        }
      } else {
        const permission = await requestPermission()
        if (permission !== 'granted') {
          toast.error('Notification permission denied')
          return
        }
        if (!user) return
        const subscription = await subscribeToPush(user.id)
        if (subscription) {
          setPushEnabled(true)
          toast.success('Push notifications enabled')
        } else {
          toast.error('Could not enable push notifications')
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to toggle notifications'
      toast.error(msg)
    } finally {
      setPushLoading(false)
    }
  }

  if (!user) return null

  return (
    <div className="px-4 pt-6 pb-8 max-w-lg mx-auto space-y-5">
      {/* Profile Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center py-6"
      >
        <Avatar name={user.name} src={user.avatarUrl} size="xl" className="mb-4 shadow-xl" />
        <h2 className="text-xl font-bold text-slate-100">{user.name}</h2>
        <p className="text-sm text-slate-400">{user.email}</p>
        <p className="text-xs text-slate-600 mt-1">
          Member since {formatDate(user.createdAt)}
        </p>
      </motion.div>

      {/* Edit Name */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-300">
            Display Name
          </h3>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
            >
              <Edit2 size={15} />
            </button>
          )}
        </div>

        {isEditing ? (
          <form onSubmit={handleSubmit(onSave)} className="space-y-3">
            <Input
              placeholder="Your name"
              error={errors.name?.message}
              autoFocus
              {...register('name')}
            />
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleCancel}
                className="gap-1"
              >
                <X size={14} />
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                loading={updating}
                className="gap-1"
              >
                <Check size={14} />
                Save
              </Button>
            </div>
          </form>
        ) : (
          <p className="text-slate-100 font-medium">{user.name}</p>
        )}
      </Card>

      {/* Account Info */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Account</h3>
        <div className="space-y-3">
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Email</p>
            <p className="text-sm text-slate-200">{user.email}</p>
          </div>
          <div className="h-px bg-slate-700" />
          <div>
            <p className="text-xs text-slate-500 mb-0.5">User ID</p>
            <p className="text-xs text-slate-500 font-mono truncate">{user.id}</p>
          </div>
        </div>
      </Card>

      {/* Push Notifications */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-600/20 flex items-center justify-center">
              <Bell size={18} className="text-primary-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Push Notifications
              </p>
              <p className="text-xs text-slate-500">
                {window.location.hostname === 'localhost'
                  ? 'Requires deployment on HTTPS'
                  : 'Get notified about new expenses'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {pushLoading && (
              <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
            )}
            <div
              onClick={!pushLoading && window.location.hostname !== 'localhost' ? handlePushToggle : undefined}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                window.location.hostname === 'localhost'
                  ? 'bg-slate-800 cursor-not-allowed opacity-40'
                  : `cursor-pointer ${pushEnabled ? 'bg-primary-600' : 'bg-slate-700'} ${pushLoading ? 'opacity-50 cursor-not-allowed' : ''}`
              }`}
            >
              <div
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform shadow ${
                  pushEnabled ? 'translate-x-5' : ''
                }`}
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Logout */}
      <div className="pt-2">
        <Button
          variant="danger"
          fullWidth
          size="lg"
          loading={loggingOut}
          onClick={() => logout()}
          className="gap-2"
        >
          <LogOut size={18} />
          Sign out
        </Button>
      </div>
    </div>
  )
}

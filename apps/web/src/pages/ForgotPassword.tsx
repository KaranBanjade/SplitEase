import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import { Mail, ChevronLeft, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useForgotPassword } from '@/hooks/useAuth'

const schema = z.object({
  email: z.string().email('Invalid email address'),
})

type ForgotForm = z.infer<typeof schema>

export default function ForgotPassword() {
  const [submitted, setSubmitted] = useState(false)
  const { mutate: forgotPassword, isPending } = useForgotPassword()

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<ForgotForm>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: ForgotForm) => {
    forgotPassword(data.email, {
      onSuccess: () => setSubmitted(true),
    })
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-sm mx-auto"
      >
        <Link
          to="/login"
          className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200 transition-colors mb-8"
        >
          <ChevronLeft size={16} />
          Back to sign in
        </Link>

        <AnimatePresence mode="wait">
          {!submitted ? (
            <motion.div
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="mb-8">
                <h1 className="text-2xl font-bold text-slate-100">
                  Forgot password?
                </h1>
                <p className="text-slate-400 text-sm mt-2">
                  Enter your email and we&apos;ll send you a reset link.
                </p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <Input
                  label="Email"
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  leftIcon={<Mail size={16} />}
                  error={errors.email?.message}
                  {...register('email')}
                />

                <Button
                  type="submit"
                  fullWidth
                  size="lg"
                  loading={isPending}
                >
                  Send reset link
                </Button>
              </form>
            </motion.div>
          ) : (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-8"
            >
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 size={32} className="text-emerald-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-100 mb-2">
                Check your email
              </h2>
              <p className="text-slate-400 text-sm mb-6">
                We sent a password reset link to{' '}
                <span className="text-slate-200 font-medium">
                  {getValues('email')}
                </span>
              </p>
              <Link to="/login">
                <Button variant="secondary" fullWidth>
                  Back to sign in
                </Button>
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

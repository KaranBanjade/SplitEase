import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/api/auth'

export function useLogin() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: () => {
      queryClient.invalidateQueries()
      navigate('/', { replace: true })
    },
    onError: (error: unknown) => {
      const axiosError = error as {
        response?: { data?: { detail?: string; message?: string } }
      }
      const msg =
        axiosError.response?.data?.detail ??
        axiosError.response?.data?.message ??
        'Login failed. Check your email and password.'
      toast.error(msg)
    },
  })
}

export function useRegister() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.register,
    onSuccess: () => {
      queryClient.invalidateQueries()
      navigate('/', { replace: true })
    },
    onError: (error: unknown) => {
      const axiosError = error as {
        response?: { data?: { detail?: string; message?: string } }
      }
      const msg =
        axiosError.response?.data?.detail ??
        axiosError.response?.data?.message ??
        'Registration failed.'
      toast.error(msg)
    },
  })
}

export function useLogout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.clear()
      navigate('/login', { replace: true })
    },
    onError: () => {
      queryClient.clear()
      navigate('/login', { replace: true })
    },
  })
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: authApi.forgotPassword,
    onSuccess: () => {
      toast.success('Password reset email sent')
    },
    onError: (error: unknown) => {
      const axiosError = error as {
        response?: { data?: { detail?: string; message?: string } }
      }
      toast.error(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.message ??
          'Request failed',
      )
    },
  })
}

export function useUpdateProfile() {
  return useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: () => {
      toast.success('Profile updated')
    },
    onError: (error: unknown) => {
      const axiosError = error as {
        response?: { data?: { detail?: string; message?: string } }
      }
      toast.error(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.message ??
          'Update failed',
      )
    },
  })
}

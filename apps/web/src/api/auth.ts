import apiClient from './client'
import type { User, AuthResponse } from '@/types'
import { useAuthStore } from '@/store/authStore'

export const authApi = {
  register: async (data: {
    email: string
    password: string
    name: string
  }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>('/auth/register', data)
    localStorage.setItem('splitease_refresh', res.data.refreshToken)
    useAuthStore.getState().setAuth(res.data.user, res.data.accessToken)
    return res.data
  },

  login: async (data: {
    email: string
    password: string
  }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>('/auth/login', data)
    localStorage.setItem('splitease_refresh', res.data.refreshToken)
    useAuthStore.getState().setAuth(res.data.user, res.data.accessToken)
    return res.data
  },

  logout: async (): Promise<void> => {
    const refreshToken = localStorage.getItem('splitease_refresh')
    try {
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refreshToken })
      }
    } finally {
      localStorage.removeItem('splitease_refresh')
      useAuthStore.getState().logout()
    }
  },

  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me')
    return res.data
  },

  updateMe: async (
    data: Partial<Pick<User, 'name' | 'avatarUrl'>>
  ): Promise<User> => {
    const res = await apiClient.put<User>('/auth/me', data)
    useAuthStore.getState().updateUser(res.data)
    return res.data
  },

  forgotPassword: async (email: string): Promise<void> => {
    await apiClient.post('/auth/forgot-password', { email })
  },

  resetPassword: async (data: {
    token: string
    password: string
  }): Promise<void> => {
    await apiClient.post('/auth/reset-password', data)
  },
}

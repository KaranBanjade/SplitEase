import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { groupsApi } from '@/api/groups'

export const groupKeys = {
  all: ['groups'] as const,
  detail: (id: string) => ['groups', id] as const,
  balances: (id: string) => ['groups', id, 'balances'] as const,
  simplifiedDebts: (id: string) => ['groups', id, 'simplified-debts'] as const,
}

export function useGroups() {
  return useQuery({
    queryKey: groupKeys.all,
    queryFn: groupsApi.list,
  })
}

export function useGroup(id: string) {
  return useQuery({
    queryKey: groupKeys.detail(id),
    queryFn: () => groupsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: groupsApi.create,
    onSuccess: (newGroup) => {
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      toast.success(`Group "${newGroup.name}" created`)
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { message?: string } } }
      toast.error(axiosError.response?.data?.message ?? 'Failed to create group')
    },
  })
}

export function useUpdateGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<{ name: string; description: string }> }) =>
      groupsApi.update(id, data),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(updatedGroup.id) })
      toast.success('Group updated')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { message?: string } } }
      toast.error(axiosError.response?.data?.message ?? 'Failed to update group')
    },
  })
}

export function useInviteMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, email }: { groupId: string; email: string }) =>
      groupsApi.inviteMember(groupId, email),
    onSuccess: (_member, { groupId }) => {
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(groupId) })
      toast.success('Member invited')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { message?: string } } }
      toast.error(axiosError.response?.data?.message ?? 'Failed to invite member')
    },
  })
}

export function useRemoveMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, userId }: { groupId: string; userId: string }) =>
      groupsApi.removeMember(groupId, userId),
    onSuccess: (_data, { groupId }) => {
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(groupId) })
      toast.success('Member removed')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { message?: string } } }
      toast.error(axiosError.response?.data?.message ?? 'Failed to remove member')
    },
  })
}

export function useGroupBalances(id: string) {
  return useQuery({
    queryKey: groupKeys.balances(id),
    queryFn: () => groupsApi.getBalances(id),
    enabled: !!id,
  })
}

export function useSimplifiedDebts(id: string) {
  return useQuery({
    queryKey: groupKeys.simplifiedDebts(id),
    queryFn: () => groupsApi.getSimplifiedDebts(id),
    enabled: !!id,
  })
}

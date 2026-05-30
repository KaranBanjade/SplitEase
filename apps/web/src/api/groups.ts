import apiClient from './client'
import type { Group, GroupMember, Balance, SimplifiedDebt } from '@/types'

export const groupsApi = {
  list: (): Promise<Group[]> =>
    apiClient.get<Group[]>('/groups').then((r) => r.data),

  get: (id: string): Promise<Group> =>
    apiClient.get<Group>(`/groups/${id}`).then((r) => r.data),

  create: (data: {
    name: string
    description?: string
    currency: string
  }): Promise<Group> =>
    apiClient.post<Group>('/groups', data).then((r) => r.data),

  update: (
    id: string,
    data: Partial<{ name: string; description: string }>
  ): Promise<Group> =>
    apiClient.put<Group>(`/groups/${id}`, data).then((r) => r.data),

  inviteMember: (groupId: string, email: string): Promise<GroupMember> =>
    apiClient
      .post<GroupMember>(`/groups/${groupId}/members`, { email })
      .then((r) => r.data),

  removeMember: (groupId: string, userId: string): Promise<void> =>
    apiClient
      .delete(`/groups/${groupId}/members/${userId}`)
      .then(() => undefined),

  getBalances: (groupId: string): Promise<Balance[]> =>
    apiClient
      .get<Balance[]>(`/groups/${groupId}/balances`)
      .then((r) => r.data),

  getSimplifiedDebts: (groupId: string): Promise<SimplifiedDebt[]> =>
    apiClient
      .get<SimplifiedDebt[]>(`/groups/${groupId}/simplified-debts`)
      .then((r) => r.data),
}

import apiClient from './client'
import type { Settlement } from '@/types'

export interface CreateSettlementPayload {
  groupId: string
  paidBy: string
  paidTo: string
  amount: number
  currency: string
  notes?: string
}

export const settlementsApi = {
  list: (groupId: string): Promise<Settlement[]> =>
    apiClient
      .get<Settlement[]>('/settlements', { params: { groupId } })
      .then((r) => r.data),

  create: (data: CreateSettlementPayload): Promise<Settlement> =>
    apiClient.post<Settlement>('/settlements', data).then((r) => r.data),
}

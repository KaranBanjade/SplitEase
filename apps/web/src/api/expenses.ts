import apiClient from './client'
import type {
  Expense,
  PaginatedResponse,
  RecurringExpense,
  RecurringFrequency,
  SplitType,
} from '@/types'

export interface CreateExpensePayload {
  groupId: string
  description: string
  amount: number
  currency: string
  paidBy: string
  category: string
  date: string
  splitType: SplitType
  splits: Array<{
    userId: string
    shareAmount: number
    owedAmount: number
  }>
  isRecurring: boolean
  recurringId?: string
  frequency?: RecurringFrequency
}

export type UpdateExpensePayload = Partial<Omit<CreateExpensePayload, 'groupId'>>

export interface CreateRecurringPayload {
  groupId: string
  description: string
  amount: number
  currency: string
  paidBy: string
  frequency: RecurringFrequency
  splitType: SplitType
  splits?: Array<{
    userId: string
    shareAmount: number
    owedAmount: number
  }>
}

export const expensesApi = {
  list: (params: {
    groupId?: string
    limit?: number
    offset?: number
  }): Promise<PaginatedResponse<Expense>> =>
    apiClient
      .get<PaginatedResponse<Expense>>('/expenses', { params })
      .then((r) => r.data),

  get: (id: string): Promise<Expense> =>
    apiClient.get<Expense>(`/expenses/${id}`).then((r) => r.data),

  create: (data: CreateExpensePayload): Promise<Expense> =>
    apiClient.post<Expense>('/expenses', data).then((r) => r.data),

  update: (id: string, data: UpdateExpensePayload): Promise<Expense> =>
    apiClient.put<Expense>(`/expenses/${id}`, data).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/expenses/${id}`).then(() => undefined),
}

export const recurringApi = {
  list: (groupId: string): Promise<RecurringExpense[]> =>
    apiClient
      .get<RecurringExpense[]>('/recurring', { params: { groupId } })
      .then((r) => r.data),

  create: (data: CreateRecurringPayload): Promise<RecurringExpense> =>
    apiClient.post<RecurringExpense>('/recurring', data).then((r) => r.data),

  update: (
    id: string,
    data: Partial<CreateRecurringPayload>
  ): Promise<RecurringExpense> =>
    apiClient
      .put<RecurringExpense>(`/recurring/${id}`, data)
      .then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/recurring/${id}`).then(() => undefined),
}

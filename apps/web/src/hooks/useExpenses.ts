import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { expensesApi, recurringApi } from '@/api/expenses'
import type { CreateExpensePayload, UpdateExpensePayload } from '@/api/expenses'
import type { Expense, PaginatedResponse } from '@/types'

const PAGE_SIZE = 20

export const expenseKeys = {
  all: ['expenses'] as const,
  list: (groupId?: string) => ['expenses', 'list', groupId] as const,
  detail: (id: string) => ['expenses', id] as const,
  recurring: (groupId?: string) => ['recurring', groupId] as const,
}

export function useExpenses(groupId?: string) {
  return useInfiniteQuery<PaginatedResponse<Expense>>({
    queryKey: expenseKeys.list(groupId),
    queryFn: ({ pageParam = 0 }) =>
      expensesApi.list({
        groupId,
        limit: PAGE_SIZE,
        offset: pageParam as number,
      }),
    getNextPageParam: (lastPage, allPages) => {
      const items = lastPage?.items ?? []
      const total = lastPage?.total ?? 0
      const fetched = allPages.reduce((acc, p) => acc + (p?.items?.length ?? 0), 0)
      return fetched < total && items.length > 0 ? fetched : undefined
    },
    initialPageParam: 0,
  })
}

export function useExpense(id: string) {
  return useQuery({
    queryKey: expenseKeys.detail(id),
    queryFn: () => expensesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateExpensePayload) => expensesApi.create(data),
    onMutate: async (newExpense) => {
      await queryClient.cancelQueries({ queryKey: expenseKeys.all })
      const previous = queryClient.getQueryData(expenseKeys.list(newExpense.groupId))
      return { previous }
    },
    onError: (error: unknown, newExpense, context) => {
      if (context?.previous) {
        queryClient.setQueryData(expenseKeys.list(newExpense.groupId), context.previous)
      }
      const axiosError = error as { response?: { data?: { detail?: string; message?: string } } }
      toast.error(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.message ??
          'Failed to add expense',
      )
    },
    onSuccess: (expense) => {
      // Invalidate entire expenses namespace → covers both group view and dashboard
      queryClient.invalidateQueries({ queryKey: expenseKeys.all })
      queryClient.invalidateQueries({ queryKey: ['groups', expense.groupId, 'balances'] })
      queryClient.invalidateQueries({ queryKey: ['groups', expense.groupId, 'simplified-debts'] })
      toast.success('Expense added')
    },
  })
}

export function useUpdateExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateExpensePayload }) =>
      expensesApi.update(id, data),
    onSuccess: (expense) => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all })
      queryClient.invalidateQueries({ queryKey: ['groups', expense.groupId, 'balances'] })
      queryClient.invalidateQueries({ queryKey: ['groups', expense.groupId, 'simplified-debts'] })
      toast.success('Expense updated')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string; message?: string } } }
      toast.error(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.message ??
          'Failed to update expense',
      )
    },
  })
}

export function useDeleteExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => expensesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all })
      toast.success('Expense deleted')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string; message?: string } } }
      toast.error(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.message ??
          'Failed to delete expense',
      )
    },
  })
}

export function useRecurringExpenses(groupId: string) {
  return useQuery({
    queryKey: expenseKeys.recurring(groupId),
    queryFn: () => recurringApi.list(groupId),
    enabled: !!groupId,
  })
}

export function useCreateRecurring() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: recurringApi.create,
    onSuccess: (recurring) => {
      queryClient.invalidateQueries({
        queryKey: expenseKeys.recurring(recurring.groupId),
      })
      toast.success('Recurring expense created')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { message?: string } } }
      toast.error(
        axiosError.response?.data?.message ?? 'Failed to create recurring expense'
      )
    },
  })
}

export function useDeleteRecurring() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: recurringApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      toast.success('Recurring expense deleted')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { message?: string } } }
      toast.error(
        axiosError.response?.data?.message ?? 'Failed to delete recurring expense'
      )
    },
  })
}

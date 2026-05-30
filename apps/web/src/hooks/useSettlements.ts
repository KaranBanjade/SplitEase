import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { settlementsApi } from '@/api/settlements'
import type { CreateSettlementPayload } from '@/api/settlements'
import { useQuery } from '@tanstack/react-query'

export const settlementKeys = {
  list: (groupId: string) => ['settlements', groupId] as const,
}

export function useSettlements(groupId: string) {
  return useQuery({
    queryKey: settlementKeys.list(groupId),
    queryFn: () => settlementsApi.list(groupId),
    enabled: !!groupId,
  })
}

export function useCreateSettlement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateSettlementPayload) => settlementsApi.create(data),
    onSuccess: (settlement) => {
      queryClient.invalidateQueries({ queryKey: settlementKeys.list(settlement.groupId) })
      queryClient.invalidateQueries({ queryKey: ['groups', settlement.groupId, 'balances'] })
      queryClient.invalidateQueries({ queryKey: ['groups', settlement.groupId, 'simplified-debts'] })
      // Dashboard reads expense splits to compute owed/owe — settlements mark splits as settled
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      toast.success('Settlement recorded')
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string; message?: string } } }
      toast.error(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.message ??
          'Failed to record settlement',
      )
    },
  })
}

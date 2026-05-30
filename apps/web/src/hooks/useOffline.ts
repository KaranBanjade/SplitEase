import { useEffect, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useOfflineStore } from '@/store/offlineStore'
import { expensesApi } from '@/api/expenses'
import { settlementsApi } from '@/api/settlements'
import type { CreateExpensePayload, UpdateExpensePayload } from '@/api/expenses'
import type { CreateSettlementPayload } from '@/api/settlements'

export function useOffline() {
  const { queue, isOnline, removeFromQueue, setOnline } = useOfflineStore()
  const queryClient = useQueryClient()

  const processQueue = useCallback(async () => {
    if (!isOnline || queue.length === 0) return

    for (const action of queue) {
      try {
        switch (action.type) {
          case 'CREATE_EXPENSE': {
            const expense = await expensesApi.create(
              action.payload as CreateExpensePayload
            )
            queryClient.invalidateQueries({
              queryKey: ['expenses', 'list', expense.groupId],
            })
            break
          }
          case 'UPDATE_EXPENSE': {
            const { id, data } = action.payload as {
              id: string
              data: UpdateExpensePayload
            }
            await expensesApi.update(id, data)
            queryClient.invalidateQueries({ queryKey: ['expenses'] })
            break
          }
          case 'DELETE_EXPENSE': {
            await expensesApi.delete(action.payload as string)
            queryClient.invalidateQueries({ queryKey: ['expenses'] })
            break
          }
          case 'CREATE_SETTLEMENT': {
            const settlement = await settlementsApi.create(
              action.payload as CreateSettlementPayload
            )
            queryClient.invalidateQueries({
              queryKey: ['settlements', settlement.groupId],
            })
            break
          }
        }
        removeFromQueue(action.id)
      } catch {
        // Keep in queue for retry
      }
    }

    if (queue.length > 0) {
      toast.success('Offline changes synced')
    }
  }, [isOnline, queue, removeFromQueue, queryClient])

  useEffect(() => {
    const handleOnline = () => {
      setOnline(true)
    }
    const handleOffline = () => {
      setOnline(false)
      toast('You are offline. Changes will sync when reconnected.', {
        icon: '📡',
      })
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [setOnline])

  useEffect(() => {
    if (isOnline && queue.length > 0) {
      processQueue()
    }
  }, [isOnline, queue.length, processQueue])

  return { isOnline, queueLength: queue.length }
}

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface OfflineAction {
  id: string
  type:
    | 'CREATE_EXPENSE'
    | 'CREATE_SETTLEMENT'
    | 'UPDATE_EXPENSE'
    | 'DELETE_EXPENSE'
  payload: unknown
  timestamp: number
  retries: number
}

interface OfflineState {
  queue: OfflineAction[]
  isOnline: boolean
  addToQueue: (action: Omit<OfflineAction, 'id' | 'timestamp' | 'retries'>) => void
  removeFromQueue: (id: string) => void
  clearQueue: () => void
  setOnline: (online: boolean) => void
}

export const useOfflineStore = create<OfflineState>()(
  persist(
    (set) => ({
      queue: [],
      isOnline: navigator.onLine,
      addToQueue: (action) =>
        set((s) => ({
          queue: [
            ...s.queue,
            {
              ...action,
              id: `offline-${Date.now()}-${Math.random().toString(36).slice(2)}`,
              timestamp: Date.now(),
              retries: 0,
            },
          ],
        })),
      removeFromQueue: (id) =>
        set((s) => ({ queue: s.queue.filter((a) => a.id !== id) })),
      clearQueue: () => set({ queue: [] }),
      setOnline: (isOnline) => set({ isOnline }),
    }),
    {
      name: 'splitease-offline-queue',
      partialize: (s) => ({ queue: s.queue }),
    }
  )
)

export function initOfflineListener() {
  const handleOnline = () => useOfflineStore.getState().setOnline(true)
  const handleOffline = () => useOfflineStore.getState().setOnline(false)

  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)

  return () => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  }
}

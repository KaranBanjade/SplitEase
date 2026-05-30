import { openDB, type DBSchema, type IDBPDatabase } from 'idb'
import type { Group, Expense, Settlement } from '@/types'
import type { OfflineAction } from '@/store/offlineStore'

interface SplitEaseDB extends DBSchema {
  groups: {
    key: string
    value: Group
  }
  expenses: {
    key: string
    value: Expense
    indexes: { 'by-group': string }
  }
  settlements: {
    key: string
    value: Settlement
    indexes: { 'by-group': string }
  }
  'offline-queue': {
    key: string
    value: OfflineAction
  }
}

let dbInstance: IDBPDatabase<SplitEaseDB> | null = null

async function getDB(): Promise<IDBPDatabase<SplitEaseDB>> {
  if (dbInstance) return dbInstance
  dbInstance = await openDB<SplitEaseDB>('splitease-db', 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('groups')) {
        db.createObjectStore('groups', { keyPath: 'id' })
      }
      if (!db.objectStoreNames.contains('expenses')) {
        const expenseStore = db.createObjectStore('expenses', { keyPath: 'id' })
        expenseStore.createIndex('by-group', 'groupId')
      }
      if (!db.objectStoreNames.contains('settlements')) {
        const settlementStore = db.createObjectStore('settlements', {
          keyPath: 'id',
        })
        settlementStore.createIndex('by-group', 'groupId')
      }
      if (!db.objectStoreNames.contains('offline-queue')) {
        db.createObjectStore('offline-queue', { keyPath: 'id' })
      }
    },
  })
  return dbInstance
}

export const db = {
  groups: {
    getAll: async (): Promise<Group[]> => {
      const database = await getDB()
      return database.getAll('groups')
    },
    get: async (id: string): Promise<Group | undefined> => {
      const database = await getDB()
      return database.get('groups', id)
    },
    put: async (group: Group): Promise<void> => {
      const database = await getDB()
      await database.put('groups', group)
    },
    del: async (id: string): Promise<void> => {
      const database = await getDB()
      await database.delete('groups', id)
    },
  },
  expenses: {
    getAll: async (): Promise<Expense[]> => {
      const database = await getDB()
      return database.getAll('expenses')
    },
    getByGroup: async (groupId: string): Promise<Expense[]> => {
      const database = await getDB()
      return database.getAllFromIndex('expenses', 'by-group', groupId)
    },
    get: async (id: string): Promise<Expense | undefined> => {
      const database = await getDB()
      return database.get('expenses', id)
    },
    put: async (expense: Expense): Promise<void> => {
      const database = await getDB()
      await database.put('expenses', expense)
    },
    del: async (id: string): Promise<void> => {
      const database = await getDB()
      await database.delete('expenses', id)
    },
  },
  settlements: {
    getAll: async (): Promise<Settlement[]> => {
      const database = await getDB()
      return database.getAll('settlements')
    },
    getByGroup: async (groupId: string): Promise<Settlement[]> => {
      const database = await getDB()
      return database.getAllFromIndex('settlements', 'by-group', groupId)
    },
    get: async (id: string): Promise<Settlement | undefined> => {
      const database = await getDB()
      return database.get('settlements', id)
    },
    put: async (settlement: Settlement): Promise<void> => {
      const database = await getDB()
      await database.put('settlements', settlement)
    },
    del: async (id: string): Promise<void> => {
      const database = await getDB()
      await database.delete('settlements', id)
    },
  },
  offlineQueue: {
    getAll: async (): Promise<OfflineAction[]> => {
      const database = await getDB()
      return database.getAll('offline-queue')
    },
    put: async (action: OfflineAction): Promise<void> => {
      const database = await getDB()
      await database.put('offline-queue', action)
    },
    del: async (id: string): Promise<void> => {
      const database = await getDB()
      await database.delete('offline-queue', id)
    },
    clear: async (): Promise<void> => {
      const database = await getDB()
      await database.clear('offline-queue')
    },
  },
}

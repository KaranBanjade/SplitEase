export interface User {
  id: string
  email: string
  name: string
  avatarUrl?: string
  createdAt: string
}

export interface Group {
  id: string
  name: string
  description?: string
  currency: string
  createdBy: string
  members: GroupMember[]
  createdAt: string
  updatedAt: string
}

export interface GroupMember {
  userId: string
  user: User
  role: 'owner' | 'member'
  joinedAt: string
}

export type SplitType = 'equal' | 'exact' | 'percentage'

export interface Expense {
  id: string
  groupId: string
  description: string
  amount: number
  currency: string
  paidBy: string
  paidByUser: User
  category: string
  date: string
  splitType: SplitType
  splits: ExpenseSplit[]
  isRecurring: boolean
  recurringId?: string
  createdAt: string
  updatedAt: string
}

export interface ExpenseSplit {
  userId: string
  user: User
  shareAmount: number
  owedAmount: number
  settledAt?: string
}

export interface Settlement {
  id: string
  groupId: string
  paidBy: string
  paidByUser: User
  paidTo: string
  paidToUser: User
  amount: number
  currency: string
  notes?: string
  createdAt: string
}

export interface Balance {
  userId: string
  user: User
  amount: number
}

export interface SimplifiedDebt {
  fromUserId: string
  fromUser: User
  toUserId: string
  toUser: User
  amount: number
  currency: string
}

export type RecurringFrequency = 'daily' | 'weekly' | 'monthly' | 'yearly'

export interface RecurringExpense {
  id: string
  groupId: string
  description: string
  amount: number
  currency: string
  paidBy: string
  frequency: RecurringFrequency
  nextDue: string
  isActive: boolean
  splitType: SplitType
  createdAt: string
}

export interface AuthResponse {
  accessToken: string
  refreshToken: string
  user: User
}

export interface ApiError {
  message: string
  detail?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

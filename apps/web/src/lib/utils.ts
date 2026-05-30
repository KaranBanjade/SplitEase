import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format, parseISO } from 'date-fns'
import type { SplitType } from '@/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number, currency = 'INR'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return format(d, 'MMM d, yyyy')
}

export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return formatDistanceToNow(d, { addSuffix: true })
}

export function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
}

export interface SplitEntry {
  userId: string
  shareAmount: number
  owedAmount: number
}

export function getSplitAmount(
  total: number,
  splitType: SplitType,
  splits: SplitEntry[],
  userId: string
): number {
  const split = splits.find((s) => s.userId === userId)
  if (!split) return 0

  if (splitType === 'equal') {
    return splits.length > 0 ? total / splits.length : 0
  }

  if (splitType === 'exact') {
    return split.owedAmount
  }

  if (splitType === 'percentage') {
    return split.shareAmount
  }

  return 0
}

export function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    food: '🍔',
    transport: '🚗',
    accommodation: '🏠',
    entertainment: '🎬',
    utilities: '💡',
    groceries: '🛒',
    health: '💊',
    shopping: '🛍️',
    travel: '✈️',
    other: '💰',
  }
  return icons[category.toLowerCase()] ?? '💰'
}

export const CATEGORIES = [
  'Food',
  'Transport',
  'Accommodation',
  'Entertainment',
  'Utilities',
  'Groceries',
  'Health',
  'Shopping',
  'Travel',
  'Other',
]

export const CURRENCIES = [
  { code: 'INR', label: 'Indian Rupee' },
  { code: 'USD', label: 'US Dollar' },
  { code: 'EUR', label: 'Euro' },
  { code: 'GBP', label: 'British Pound' },
  { code: 'CAD', label: 'Canadian Dollar' },
  { code: 'AUD', label: 'Australian Dollar' },
  { code: 'JPY', label: 'Japanese Yen' },
  { code: 'SGD', label: 'Singapore Dollar' },
]

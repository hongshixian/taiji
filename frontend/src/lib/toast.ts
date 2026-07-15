import { reactive } from 'vue'

export type ToastTone = 'success' | 'error' | 'warning' | 'info'

export interface ToastItem {
  id: number
  tone: ToastTone
  message: string
}

let seq = 0
export const toasts = reactive<ToastItem[]>([])

function push(tone: ToastTone, message: string, duration = 3000) {
  const id = ++seq
  toasts.push({ id, tone, message })
  setTimeout(() => dismiss(id), duration)
}

export function dismiss(id: number) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i !== -1) toasts.splice(i, 1)
}

export const toast = {
  success: (m: string) => push('success', m),
  error: (m: string) => push('error', m, 4500),
  warning: (m: string) => push('warning', m),
  info: (m: string) => push('info', m),
}

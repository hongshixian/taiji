import { i18n } from '@/i18n'

export type StatusTone = 'success' | 'warning' | 'info' | 'danger' | 'neutral' | 'brand'

// 任务状态 → 展示 tone / 文案 的统一映射
const TONE: Record<string, StatusTone> = {
  pending: 'warning',
  running: 'info',
  success: 'success',
  failed: 'danger',
  timeout: 'warning',
}

export function taskStatusTone(status: string): StatusTone {
  return TONE[status] || 'neutral'
}

// 文案走 i18n（taskStatus.* 命名空间）；缺失时回退原值。
// t() 读取 locale.value，在模板/computed 内调用即随语言切换响应式更新。
export function taskStatusLabel(status: string): string {
  const key = `taskStatus.${status}`
  const g = i18n.global
  return g.te(key) ? (g.t(key) as string) : status
}

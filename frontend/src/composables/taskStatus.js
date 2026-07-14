// 任务状态 → 展示 tone / 文案 的统一映射
const TONE = {
  pending: 'warning',
  running: 'info',
  success: 'success',
  failed: 'danger',
  timeout: 'warning',
}

const LABEL = {
  pending: '等待中',
  running: '执行中',
  success: '成功',
  failed: '失败',
  timeout: '仍在执行',
}

export function taskStatusTone(status) {
  return TONE[status] || 'neutral'
}

export function taskStatusLabel(status) {
  return LABEL[status] || status
}

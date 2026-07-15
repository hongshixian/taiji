import { reactive } from 'vue'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  tone?: 'default' | 'danger'
}

interface ConfirmState extends ConfirmOptions {
  open: boolean
  _resolve?: (ok: boolean) => void
}

export const confirmState = reactive<ConfirmState>({
  open: false,
  message: '',
})

/** 命令式确认框，返回 Promise<boolean> */
export function confirm(opts: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    confirmState.title = opts.title ?? '确认'
    confirmState.message = opts.message
    confirmState.confirmText = opts.confirmText ?? '确认'
    confirmState.cancelText = opts.cancelText ?? '取消'
    confirmState.tone = opts.tone ?? 'default'
    confirmState.open = true
    confirmState._resolve = resolve
  })
}

export function resolveConfirm(ok: boolean) {
  confirmState.open = false
  confirmState._resolve?.(ok)
  confirmState._resolve = undefined
}

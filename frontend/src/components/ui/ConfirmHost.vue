<template>
  <UiDialog :model-value="confirmState.open" :title="confirmState.title" width="420px" @update:model-value="onCancel">
    <p class="text-sm text-fg-secondary">{{ confirmState.message }}</p>
    <template #footer>
      <UiButton variant="secondary" @click="onCancel">{{ confirmState.cancelText }}</UiButton>
      <UiButton :variant="confirmState.tone === 'danger' ? 'danger' : 'primary'" @click="onOk">
        {{ confirmState.confirmText }}
      </UiButton>
    </template>
  </UiDialog>
</template>

<script setup lang="ts">
import UiDialog from './Dialog.vue'
import UiButton from './Button.vue'
import { confirmState, resolveConfirm } from '@/lib/confirm'

function onOk() {
  resolveConfirm(true)
}
function onCancel() {
  resolveConfirm(false)
}
</script>

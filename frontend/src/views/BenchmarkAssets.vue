<template>
  <div class="page-shell page-shell--wide flex flex-col gap-8">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('benchmarkAssets.eyebrow') }}</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="page-header__title">{{ t('benchmarkAssets.title') }}</h1>
        <UiButton variant="secondary" size="sm" :loading="loading" @click="loadAssets">
          {{ t('common.refresh') }}
        </UiButton>
      </div>
      <p class="page-header__lede">{{ t('benchmarkAssets.lede') }}</p>
    </header>

    <section class="flex flex-col gap-6 rounded-lg border border-line bg-surface p-6 shadow-xs">
      <UiTable :columns="columns" :data="rows" row-key="key" stripe :loading="loading">
        <template #cell-display_name="{ row }">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-2">
              <span class="font-medium text-fg">{{ (row as SuiteAsset).display_name }}</span>
              <UiBadge v-if="(row as SuiteAsset).gated" tone="warning" :label="t('benchmarkAssets.gated')" />
            </div>
            <span class="font-mono text-2xs text-fg-tertiary">{{ (row as SuiteAsset).key }}</span>
          </div>
        </template>
        <template #cell-data_source="{ row }">
          <UiBadge :tone="dataSourceTone((row as SuiteAsset).data_source)" :label="dataSourceLabel((row as SuiteAsset).data_source)" />
        </template>
        <template #cell-needs_judge="{ row }">
          <span :class="(row as SuiteAsset).needs_judge ? 'text-fg' : 'text-fg-tertiary'">
            {{ (row as SuiteAsset).needs_judge ? t('common.yes') : t('common.no') }}
          </span>
        </template>
        <template #cell-needs_sandbox="{ row }">
          <span :class="(row as SuiteAsset).needs_sandbox ? 'text-fg' : 'text-fg-tertiary'">
            {{ (row as SuiteAsset).needs_sandbox ? t('common.yes') : t('common.no') }}
          </span>
        </template>
        <template #cell-enabled="{ row }">
          <div class="flex items-center gap-2">
            <UiSwitch
              :model-value="(row as SuiteAsset).effective_enabled"
              :disabled="!canWrite || (row as SuiteAsset).needs_sandbox || togglingKeys.has((row as SuiteAsset).key)"
              @update:model-value="(v) => onToggle(row as SuiteAsset, v)"
            />
          </div>
        </template>
        <template #cell-sample_count="{ row }">
          <span v-if="(row as SuiteAsset).sample_count != null" class="font-mono text-sm text-fg">{{ (row as SuiteAsset).sample_count!.toLocaleString() }}</span>
          <span v-else class="text-fg-tertiary">—</span>
        </template>
        <template #cell-readiness="{ row }">
          <StatusPill
            :tone="checkTone((row as SuiteAsset).last_check_status)"
            :label="checkLabel((row as SuiteAsset).last_check_status)"
            :dot="(row as SuiteAsset).last_check_status === 'pending'"
          />
        </template>
        <template #cell-actions="{ row }">
          <div class="flex items-center gap-1">
            <UiButton
              v-if="canWrite"
              variant="text"
              size="sm"
              :loading="(row as SuiteAsset).last_check_status === 'pending'"
              :disabled="(row as SuiteAsset).needs_sandbox"
              @click="onCheck(row as SuiteAsset)"
            >
              {{ (row as SuiteAsset).last_check_status === 'ok' || (row as SuiteAsset).last_check_status === 'failed' ? t('benchmarkAssets.recheckBtn') : t('benchmarkAssets.checkBtn') }}
            </UiButton>
            <UiDropdown v-if="canWrite && (row as SuiteAsset).override_enabled !== null">
              <template #trigger>
                <UiButton variant="text" size="sm"><ChevronDown class="size-4" /></UiButton>
              </template>
              <UiDropdownItem @click="onToggle(row as SuiteAsset, null)">
                {{ t('benchmarkAssets.restoreDefault') }}
              </UiDropdownItem>
            </UiDropdown>
          </div>
        </template>
      </UiTable>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { listSuiteAssets, setSuiteEnabled, checkSuiteAccess } from '@/api/benchmark'
import type { SuiteAsset, SuiteCheckStatus } from '@/api/types'
import { usePermission } from '@/composables/usePermission'
import StatusPill from '@/components/StatusPill.vue'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiSwitch from '@/components/ui/Switch.vue'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiDropdown from '@/components/ui/Dropdown.vue'
import UiDropdownItem from '@/components/ui/DropdownItem.vue'

const { t } = useI18n()
const { has } = usePermission()
const canWrite = computed(() => has('benchmark:write'))

const rows = ref<SuiteAsset[]>([])
const loading = ref(false)
const togglingKeys = ref<Set<string>>(new Set())

const columns = computed<TableColumn[]>(() => [
  { key: 'display_name', label: t('benchmarkAssets.col.name'), minWidth: 200 },
  { key: 'data_source', label: t('benchmarkAssets.col.source'), width: 130 },
  { key: 'needs_judge', label: t('benchmarkAssets.col.needsJudge'), width: 90 },
  { key: 'needs_sandbox', label: t('benchmarkAssets.col.sandbox'), width: 100 },
  { key: 'sample_count', label: t('benchmarkAssets.col.sampleCount'), width: 100, align: 'right' },
  { key: 'enabled', label: t('benchmarkAssets.col.enabled'), width: 140 },
  { key: 'readiness', label: t('benchmarkAssets.col.readiness'), width: 130 },
  { key: 'actions', label: t('common.actions'), width: 200, fixed: 'right' },
])

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollCount = 0
const MAX_POLLS = 60   // 2s * 60 = 2min，覆盖单次检测（含下载）

onMounted(loadAssets)
onBeforeUnmount(stopPoll)

async function loadAssets() {
  loading.value = true
  try {
    const { data } = await listSuiteAssets()
    rows.value = data.data.items || []
    syncPolling()
  } catch {
    toast.error(t('benchmarkAssets.loadFailed'))
  } finally {
    loading.value = false
  }
}

// 有 pending 行则开轮询，无则停
function syncPolling() {
  const hasPending = rows.value.some((r) => r.last_check_status === 'pending')
  if (hasPending && !pollTimer) startPoll()
  else if (!hasPending) stopPoll()
}

function startPoll() {
  pollCount = 0
  pollTimer = setInterval(async () => {
    pollCount++
    if (pollCount > MAX_POLLS) { stopPoll(); return }
    try {
      const { data } = await listSuiteAssets()
      const byKey = new Map<string, SuiteAsset>((data.data.items || []).map((r: SuiteAsset) => [r.key, r]))
      // 按 key 原地更新，不整体替换（避免打断表格交互）
      rows.value = rows.value.map((r) => byKey.get(r.key) ?? r)
      if (!rows.value.some((r) => r.last_check_status === 'pending')) stopPoll()
    } catch { /* silent */ }
  }, 2000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function onToggle(row: SuiteAsset, enabled: boolean | null) {
  if (togglingKeys.value.has(row.key)) return
  togglingKeys.value.add(row.key)
  const prev = { effective: row.effective_enabled, override: row.override_enabled }
  // 乐观更新
  if (enabled !== null) { row.effective_enabled = enabled; row.override_enabled = enabled }
  try {
    const { data } = await setSuiteEnabled(row.key, enabled)
    Object.assign(row, data.data)
  } catch {
    row.effective_enabled = prev.effective
    row.override_enabled = prev.override
    toast.error(t('benchmarkAssets.toggleFailed'))
  } finally {
    togglingKeys.value.delete(row.key)
  }
}

async function onCheck(row: SuiteAsset) {
  try {
    await checkSuiteAccess(row.key)
    row.last_check_status = 'pending'
    row.last_check_error = null
    syncPolling()
    toast.success(t('benchmarkAssets.checkStarted'))
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
    toast.error(msg || t('benchmarkAssets.checkFailed'))
  }
}

function dataSourceLabel(s?: string): string {
  const key = (s || 'hf') as 'hf' | 'github' | 'bundled'
  return t(`benchmarkAssets.dataSource.${key}`)
}
function dataSourceTone(s?: string): 'brand' | 'info' | 'neutral' {
  return ({ hf: 'brand', github: 'info', bundled: 'neutral' } as const)[(s || 'hf') as 'hf' | 'github' | 'bundled'] || 'neutral'
}
function checkTone(s: SuiteCheckStatus): 'success' | 'danger' | 'warning' | 'neutral' {
  return { ok: 'success', failed: 'danger', pending: 'warning', unknown: 'neutral' }[s] as 'success' | 'danger' | 'warning' | 'neutral'
}
function checkLabel(s: SuiteCheckStatus): string {
  return t(`benchmarkAssets.status.${s}`)
}
</script>

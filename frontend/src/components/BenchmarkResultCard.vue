<template>
  <div class="benchmark-result">
    <!-- 失败且无结果：突出错误 -->
    <el-alert
      v-if="task.status === 'failed' && task.error_message"
      type="error"
      :closable="false"
      show-icon
      title="评测执行失败"
      class="result-error-alert"
    >
      <pre class="result-error-text">{{ task.error_message }}</pre>
    </el-alert>

    <!-- 无任何结果 -->
    <div v-if="!hasResult" class="result-empty--large">
      <el-icon :size="28"><DataAnalysis /></el-icon>
      <span>{{ task.status === 'failed' ? '任务失败，未产出结果' : '任务尚未产出结果' }}</span>
    </div>

    <template v-else>
      <!-- 概览卡片组 -->
      <div class="result-cards">
        <div class="result-card">
          <div class="result-card__title">主要指标</div>
          <div v-if="metricEntries.length" class="result-card__body">
            <div v-for="[k, v] in metricEntries" :key="k" class="metric-row">
              <span class="metric-name t-mono">{{ k }}</span>
              <span class="metric-value t-mono">{{ formatMetric(v) }}</span>
            </div>
          </div>
          <div v-else class="result-empty">暂无指标</div>
        </div>

        <div class="result-card">
          <div class="result-card__title">样本统计</div>
          <div class="result-card__body">
            <div class="metric-row">
              <span class="metric-name">总数</span>
              <span class="metric-value t-mono">{{ result.total_samples ?? '—' }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-name">已完成</span>
              <span class="metric-value t-mono">{{ result.completed_samples ?? '—' }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-name">失败</span>
              <span class="metric-value t-mono" :class="{ 'text-danger': result.failed_samples }">
                {{ result.failed_samples ?? 0 }}
              </span>
            </div>
            <div class="metric-row">
              <span class="metric-name">状态</span>
              <StatusPill :tone="statusTone(result.status || task.status)" :label="statusLabel(result.status || task.status)" />
            </div>
          </div>
        </div>

        <div class="result-card">
          <div class="result-card__title">Token 消耗</div>
          <div class="result-card__body">
            <div class="metric-row">
              <span class="metric-name">输入</span>
              <span class="metric-value t-mono">{{ fmtNum(result.model_usage?.input_tokens) }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-name">输出</span>
              <span class="metric-value t-mono">{{ fmtNum(result.model_usage?.output_tokens) }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-name">合计</span>
              <span class="metric-value t-mono">{{ fmtNum(result.model_usage?.total_tokens) }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-name">引擎</span>
              <span class="metric-value t-mono">{{ result.engine || '—' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 任务元信息 -->
      <div class="result-meta">
        <div class="meta-row"><span class="meta-label">Suite</span><span class="t-mono">{{ task.benchmark_suite }}</span></div>
        <div class="meta-row"><span class="meta-label">被测</span><span>{{ task.target_model?.display_name || '—' }}</span></div>
        <div class="meta-row"><span class="meta-label">评委</span><span>{{ task.judge_model?.display_name || '（无）' }}</span></div>
      </div>

      <!-- 样本预览 -->
      <div v-if="result.samples_preview?.length" class="samples-preview">
        <div class="samples-preview__header">
          <span class="result-card__title">样本预览（前 {{ result.samples_preview.length }} 条）</span>
          <el-button size="small" text @click="$emit('view-log')">查看完整日志</el-button>
        </div>
        <el-collapse>
          <el-collapse-item
            v-for="s in result.samples_preview"
            :key="s.id"
            :name="String(s.id)"
          >
            <template #title>
              <span class="sample-id t-mono">#{{ s.id }}</span>
              <StatusPill :tone="sampleTone(s.score)" :label="String(s.score || '—')" />
            </template>
            <div class="sample-body">
              <div class="sample-block">
                <div class="sample-label">Input</div>
                <div class="sample-text">{{ s.input || '—' }}</div>
              </div>
              <div class="sample-block">
                <div class="sample-label">Target</div>
                <div class="sample-text">{{ s.target || '—' }}</div>
              </div>
              <div class="sample-block">
                <div class="sample-label">Output</div>
                <div class="sample-text">{{ s.output || '—' }}</div>
              </div>
              <div v-if="s.explanation" class="sample-block">
                <div class="sample-label">Explanation</div>
                <div class="sample-text">{{ s.explanation }}</div>
              </div>
              <div v-if="s.error" class="sample-block sample-block--error">
                <div class="sample-label">Error</div>
                <div class="sample-text">{{ s.error }}</div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import StatusPill from './StatusPill.vue'
import { taskStatusTone as statusTone, taskStatusLabel as statusLabel } from '../composables/taskStatus'

const props = defineProps({
  task: { type: Object, required: true },
})
defineEmits(['view-log'])

const result = computed(() => props.task.result || {})
const metricEntries = computed(() => Object.entries(result.value.metrics || {}))
const hasResult = computed(() => {
  const r = result.value
  return !!(r.metrics && Object.keys(r.metrics).length) ||
         !!(r.samples_preview && r.samples_preview.length) ||
         r.total_samples > 0
})

function formatMetric(v) {
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v.toString() : v.toFixed(4)
  }
  return v
}

function fmtNum(v) {
  if (v == null) return '—'
  return typeof v === 'number' ? v.toLocaleString() : v
}

function sampleTone(score) {
  const s = String(score || '').toUpperCase()
  if (s === 'C' || s === 'CORRECT' || s === '1' || s === 'TRUE') return 'success'
  if (s === 'I' || s === 'INCORRECT' || s === '0' || s === 'FALSE') return 'danger'
  return 'neutral'
}
</script>

<style scoped>
.benchmark-result {
  padding: var(--space-2) 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.result-error-alert { align-items: flex-start; }
.result-error-text {
  margin: var(--space-2) 0 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 160px;
  overflow: auto;
}
.result-empty--large {
  padding: var(--space-10);
  text-align: center;
  color: var(--fg-tertiary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}
.result-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-5);
}
.result-card {
  background: var(--bg-surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-6);
}
.result-card__title {
  font-weight: var(--weight-semibold);
  margin-bottom: var(--space-5);
  color: var(--fg-primary);
}
.result-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}
.metric-name { color: var(--fg-secondary); font-size: var(--text-sm); }
.metric-value { font-weight: var(--weight-semibold); color: var(--fg-primary); }
.text-danger { color: var(--color-danger-fg); }
.result-empty { color: var(--fg-tertiary); font-size: var(--text-sm); }

.result-meta {
  background: var(--bg-surface);
  padding: var(--space-4) var(--space-6);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4) var(--space-8);
}
.meta-row { display: flex; gap: var(--space-3); align-items: center; font-size: var(--text-sm); }
.meta-label { color: var(--fg-tertiary); }

.samples-preview {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-6);
}
.samples-preview__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}
.sample-id { margin-right: var(--space-4); color: var(--fg-secondary); }
.sample-body { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-3) 0; }
.sample-block { display: flex; flex-direction: column; gap: var(--space-2); }
.sample-block--error .sample-text { color: var(--color-danger-fg); background: var(--color-danger-bg); }
.sample-label { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em; color: var(--fg-tertiary); }
.sample-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--bg-surface-sunken);
  padding: var(--space-4);
  border-radius: var(--radius-sm);
}
</style>

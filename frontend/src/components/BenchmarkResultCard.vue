<template>
  <div class="benchmark-result">
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
            <span class="metric-value t-mono">{{ result.failed_samples ?? 0 }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">状态</span>
            <span class="metric-value">{{ result.status || task.status }}</span>
          </div>
        </div>
      </div>

      <div class="result-card">
        <div class="result-card__title">Token 消耗</div>
        <div class="result-card__body">
          <div class="metric-row">
            <span class="metric-name">输入</span>
            <span class="metric-value t-mono">{{ result.model_usage?.input_tokens ?? '—' }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">输出</span>
            <span class="metric-value t-mono">{{ result.model_usage?.output_tokens ?? '—' }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">合计</span>
            <span class="metric-value t-mono">{{ result.model_usage?.total_tokens ?? '—' }}</span>
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
      <div class="meta-row"><span>Suite</span><span class="t-mono">{{ task.benchmark_suite }}</span></div>
      <div class="meta-row"><span>引擎</span><span class="t-mono">{{ task.engine }}</span></div>
      <div class="meta-row"><span>被测</span><span>{{ task.target_model?.display_name || '—' }}</span></div>
      <div class="meta-row"><span>评委</span><span>{{ task.judge_model?.display_name || '（无）' }}</span></div>
      <div v-if="task.error_message" class="meta-row meta-error">
        <span>错误</span><span>{{ task.error_message }}</span>
      </div>
    </div>

    <!-- 样本预览 -->
    <div v-if="result.samples_preview?.length" class="samples-preview">
      <div class="result-card__title">
        样本预览（前 {{ result.samples_preview.length }} 条）
        <el-button size="small" text @click="$emit('view-log')">查看完整日志</el-button>
      </div>
      <el-collapse>
        <el-collapse-item
          v-for="s in result.samples_preview"
          :key="s.id"
          :name="String(s.id)"
        >
          <template #title>
            <span class="sample-id">#{{ s.id }}</span>
            <span class="status-pill" :data-tone="sampleTone(s.score)">
              {{ s.score || '—' }}
            </span>
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

    <div v-if="!result.metrics && !result.samples_preview?.length" class="result-empty result-empty--large">
      任务尚未产出结果
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: { type: Object, required: true },
})
defineEmits(['view-log'])

const result = computed(() => props.task.result || {})
const metricEntries = computed(() => Object.entries(result.value.metrics || {}))

function formatMetric(v) {
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v.toString() : v.toFixed(4)
  }
  return v
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
  padding: var(--space-2, 8px) 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.result-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-3, 12px);
}
.result-card {
  background: var(--color-surface-2, #f7f8fb);
  border-radius: 10px;
  padding: var(--space-4, 16px);
}
.result-card__title {
  font-weight: 600;
  margin-bottom: var(--space-3, 12px);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.metric-name {
  color: var(--color-text-3, #666);
  font-size: 13px;
}
.metric-value {
  font-weight: 600;
}
.result-empty {
  color: var(--color-text-3, #999);
  font-size: 13px;
}
.result-empty--large {
  padding: var(--space-6, 24px);
  text-align: center;
}
.result-meta {
  background: var(--color-surface-1, #fff);
  padding: var(--space-3, 12px);
  border-radius: 8px;
  border: 1px solid var(--color-border-subtle, #eef);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3, 12px) var(--space-5, 20px);
}
.meta-row { display: flex; gap: 8px; align-items: center; font-size: 13px; }
.meta-row span:first-child { color: var(--color-text-3, #999); }
.meta-error { color: var(--color-danger, #c94040); }

.samples-preview {
  background: var(--color-surface-1, #fff);
  border: 1px solid var(--color-border-subtle, #eef);
  border-radius: 10px;
  padding: var(--space-4, 16px);
}
.sample-id { font-family: var(--font-mono, monospace); margin-right: 8px; }
.sample-body { display: flex; flex-direction: column; gap: 8px; padding: 8px 0; }
.sample-block { display: flex; flex-direction: column; gap: 4px; }
.sample-block--error { color: var(--color-danger, #c94040); }
.sample-label { font-size: 11px; text-transform: uppercase; color: var(--color-text-3, #999); }
.sample-text {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--color-surface-2, #f6f7fb);
  padding: 8px;
  border-radius: 6px;
}

.status-pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: var(--color-neutral-100, #eee);
}
.status-pill[data-tone='success'] { background: #e6f7ea; color: #229c53; }
.status-pill[data-tone='danger'] { background: #fdecec; color: #c94040; }
</style>

<template>
  <div class="page-shell benchmark-task">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">任务 · Benchmark 测评</span>
      <div class="page-header__row">
        <h1 class="page-header__title">Benchmark 测评</h1>
        <el-button type="primary" @click="showDialog = true">
          <el-icon><Plus /></el-icon>&nbsp;新建测评
        </el-button>
      </div>
      <p class="page-header__lede">
        配置被测模型与测评套件，由 Worker 异步执行标准化 Benchmark 评测。测评结果在当前租户内可见。
      </p>
    </header>

    <section class="metric-strip">
      <div class="metric">
        <span class="t-eyebrow">进行中</span>
        <span class="t-mono metric-value">{{ activeTasks.length }}</span>
      </div>
      <div class="metric">
        <span class="t-eyebrow">历史记录</span>
        <span class="t-mono metric-value">{{ total }}</span>
      </div>
      <div class="metric">
        <span class="t-eyebrow">轮询超时</span>
        <span class="t-mono metric-value">{{ MAX_POLLS * 2 }} 秒</span>
      </div>
    </section>

    <el-dialog v-model="showDialog" title="新建 Benchmark" width="600px" :close-on-click-modal="false">
      <el-form label-width="120px" @submit.prevent>
        <el-form-item label="任务名称" required>
          <el-input v-model="form.taskName" placeholder="例：GPT-4o MMLU 测评" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="被测模型" required>
          <el-select
            v-model="selectedModelId"
            placeholder="选择已配置的模型（可选）"
            clearable
            style="width:100%"
            @change="applyModelPreset"
          >
            <el-option
              v-for="m in modelPresets"
              :key="m.id"
              :label="m.display_name"
              :value="m.id"
            >
              <span>{{ m.display_name }}</span>
              <span style="float:right;color:var(--fg-tertiary);font-size:12px;font-family:var(--font-mono)">{{ m.model_name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="Benchmark" required>
          <el-select v-model="form.benchmarkSuite" placeholder="选择 Benchmark" style="width:100%">
            <el-option-group label="基础交互安全">
              <el-option label="AIR Bench" value="air_bench" />
              <el-option label="BeaverTails" value="beavertails" />
              <el-option label="CoCoNot" value="coconot" />
              <el-option label="LongSafety" value="longsafety" />
              <el-option label="PKU SaferLHF" value="pku_saferlhf" />
              <el-option label="SafetyBench" value="safetybench" />
              <el-option label="StrongREJECT" value="strongreject" />
              <el-option label="XSTest" value="xstest" />
              <el-option label="SimpleQA Verified" value="simpleqa" />
              <el-option label="TruthfulQA" value="truthfulqa" />
              <el-option label="Sycophancy Eval" value="sycophancy_eval" />
              <el-option label="StereoSet" value="stereoset" />
              <el-option label="HealthBench" value="healthbench" />
            </el-option-group>
            <el-option-group label="工具调用与智能体安全">
              <el-option label="AgentHarm" value="agentharm" />
              <el-option label="Agent Threat Bench — 自主劫持" value="agent_threat_bench_autonomy_hijack" />
              <el-option label="Agent Threat Bench — 数据泄露" value="agent_threat_bench_data_exfil" />
              <el-option label="Agent Threat Bench — 记忆投毒" value="agent_threat_bench_memory_poison" />
              <el-option label="PersistBench — 跨域持久性" value="persistbench_cross_domain" />
              <el-option label="PersistBench — 谄媚记忆" value="persistbench_sycophancy" />
              <el-option label="Prompt Injection" value="cyse2_prompt_injection" />
              <el-option label="Make Me Pay" value="make_me_pay" />
              <el-option label="MakeMeSay" value="makemesay" />
              <el-option label="SAD" value="sad" />
              <el-option label="DeceptionBench (ARIES)" value="deceptionbench_aries" />
            </el-option-group>
            <el-option-group label="前沿风险能力">
              <el-option label="WMDP Cyber" value="wmdp_cyber" />
              <el-option label="WMDP Bio" value="wmdp_bio" />
              <el-option label="WMDP Chem" value="wmdp_chem" />
              <el-option label="BigCodeBench" value="bigcodebench" />
              <el-option label="HumanEval" value="humaneval" />
              <el-option label="MMLU" value="mmlu" />
              <el-option label="GSM8K" value="gsm8k" />
              <el-option label="HellaSWAG" value="hellaswag" />
              <el-option label="GDM Dangerous Capabilities: Stealth" value="gdm_dangerous_stealth" />
            </el-option-group>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交测评</el-button>
      </template>
    </el-dialog>
    <!-- 进行中任务卡片 -->
    <section v-if="activeTasks.length" class="task-section">
      <div class="task-section__header">
        <span class="t-eyebrow">进行中</span>
        <span class="t-caption">{{ activeTasks.length }} 个任务正在轮询</span>
      </div>
      <div class="active-list">
        <article v-for="task in activeTasks" :key="'a-' + task.id" class="active-card">
          <header class="active-card__header">
            <div class="active-card__info">
              <span class="active-card__name">{{ task.task_name || '提交中…' }}</span>
              <span v-if="task.model_name" class="active-card__model t-caption">{{ task.model_name }}</span>
            </div>
            <div class="active-card__actions">
              <span class="status-pill" :data-tone="statusTone(task.frontendStatus)">
                {{ statusLabel(task.frontendStatus) }}
              </span>
              <el-button v-if="canOpenTaskLogs(task)" text type="primary" size="small" @click="openTaskLogs(task)">日志</el-button>
            </div>
          </header>
          <el-skeleton :rows="2" animated />
          <footer class="active-card__meta">
            <span class="t-caption">已等待</span>
            <span class="t-mono">{{ task.elapsed }}s</span>
            <span class="t-caption">·</span>
            <span class="t-caption">轮询</span>
            <span class="t-mono">{{ task.pollCount }}/{{ MAX_POLLS }}</span>
          </footer>
        </article>
      </div>
    </section>

    <!-- 历史任务表格 -->
    <section v-if="historyTasks.length" class="task-section" data-density="compact">
      <div class="task-section__header">
        <span class="t-eyebrow">历史记录</span>
        <span class="t-caption">第 {{ page }} 页 · 每页 {{ perPage }} 条</span>
      </div>
      <el-table :data="historyTasks" stripe v-loading="tableLoading" class="history-table" row-key="id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-grid">
              <div class="settings-card">
                <p class="settings-card__label t-eyebrow">任务信息</p>
                <dl class="info-dl">
                  <dt>ID</dt><dd class="t-mono">{{ row.id }}</dd>
                  <dt>状态</dt>
                  <dd>
                    <span class="status-pill" :data-tone="dbStatusTone(row.status)">{{ dbStatusLabel(row.status) }}</span>
                  </dd>
                  <dt>创建时间</dt><dd class="t-mono">{{ formatTime(row.created_at) }}</dd>
                  <dt>开始时间</dt><dd class="t-mono">{{ formatTime(row.started_at) || '—' }}</dd>
                  <dt>完成时间</dt><dd class="t-mono">{{ formatTime(row.completed_at) || '—' }}</dd>
                  <dt v-if="row.error_message">错误</dt>
                  <dd v-if="row.error_message" class="error-text">{{ row.error_message }}</dd>
                </dl>
              </div>
              <div class="settings-card">
                <p class="settings-card__label t-eyebrow">被测模型</p>
                <dl class="info-dl">
                  <dt>模型名称</dt><dd>{{ row.model_name }}</dd>
                </dl>
              </div>
              <div class="settings-card">
                <p class="settings-card__label t-eyebrow">Benchmark 配置</p>
                <dl class="info-dl">
                  <dt>测评套件</dt><dd><span class="suite-badge">{{ suiteName(row.benchmark_suite) }}</span></dd>
                  <dt v-if="row.benchmark_config">配置参数</dt>
                  <dd v-if="row.benchmark_config">
                    <pre class="json-pre">{{ JSON.stringify(row.benchmark_config, null, 2) }}</pre>
                  </dd>
                  <dt v-if="!row.benchmark_config">配置参数</dt>
                  <dd v-if="!row.benchmark_config" class="t-caption">使用默认配置</dd>
                </dl>
              </div>
              <div class="settings-card result-card">
                <p class="settings-card__label t-eyebrow">测评结果</p>
                <div v-if="row.result">
                  <pre class="json-pre">{{ JSON.stringify(row.result, null, 2) }}</pre>
                </div>
                <div v-else class="result-placeholder">
                  <el-icon class="result-placeholder__icon"><DataAnalysis /></el-icon>
                  <p class="t-caption">暂无结果</p>
                  <p class="t-caption" style="color:var(--fg-tertiary)">测评完成后结果将显示在此处</p>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="任务名称" min-width="180">
          <template #default="{ row }">{{ row.task_name }}</template>
        </el-table-column>
        <el-table-column label="被测模型" min-width="160">
          <template #default="{ row }">{{ row.model_name }}</template>
        </el-table-column>
        <el-table-column label="测评套件" width="160">
          <template #default="{ row }">
            <span class="suite-badge">{{ suiteName(row.benchmark_suite) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="dbStatusTone(row.status)">{{ dbStatusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日志" width="70">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openTaskLogs(row)">日志</el-button>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span class="t-mono">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.status === 'failed'" text type="primary" size="small" @click="retryDbTask(row)">重试</el-button>
            <el-button v-if="has('task:delete:any')" text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > perPage"
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        class="pagination"
        @current-change="fetchHistoryTasks"
      />
    </section>

    <!-- 空状态 -->
    <section v-if="activeTasks.length === 0 && historyTasks.length === 0 && !tableLoading" class="empty-state">
      <span class="t-eyebrow">暂无测评</span>
      <h3 class="empty-state__title">还没有提交过 Benchmark 测评</h3>
      <p class="empty-state__lede">选择测评套件和被测模型，提交后 Worker 将在后台异步执行。</p>
      <el-button type="primary" @click="showDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;提交第一个测评
      </el-button>
    </section>

    <TaskLogDialog ref="taskLogDialogRef" />
  </div>
</template>
<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteBenchmark,
  getBenchmark,
  listBenchmarks,
  retryBenchmark,
  submitBenchmark,
} from '../api/benchmark'
import { listModels } from '../api/model'
import TaskLogDialog from '../components/TaskLogDialog.vue'
import { usePermission } from '../composables/usePermission'

const MAX_POLLS = 30
const showDialog = ref(false)
const submitting = ref(false)
const activeTasks = ref([])
const historyTasks = ref([])
const tableLoading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)
const { has } = usePermission()
const taskLogDialogRef = ref(null)
const modelPresets = ref([])
const selectedModelId = ref(null)

const SUITE_LABELS = {
  air_bench: 'AIR Bench', beavertails: 'BeaverTails', coconot: 'CoCoNot',
  longsafety: 'LongSafety', pku_saferlhf: 'PKU SaferLHF', safetybench: 'SafetyBench',
  strongreject: 'StrongREJECT', xstest: 'XSTest', simpleqa: 'SimpleQA',
  truthfulqa: 'TruthfulQA', sycophancy_eval: 'Sycophancy Eval', stereoset: 'StereoSet',
  healthbench: 'HealthBench', agentharm: 'AgentHarm',
  agent_threat_bench_autonomy_hijack: 'AgentThreat-Hijack',
  agent_threat_bench_data_exfil: 'AgentThreat-DataExfil',
  agent_threat_bench_memory_poison: 'AgentThreat-MemPoison',
  persistbench_cross_domain: 'PersistBench-CrossDomain',
  persistbench_sycophancy: 'PersistBench-Sycophancy',
  cyse2_prompt_injection: 'Prompt Injection', make_me_pay: 'Make Me Pay',
  makemesay: 'MakeMeSay', sad: 'SAD', deceptionbench_aries: 'DeceptionBench-ARIES',
  wmdp_cyber: 'WMDP Cyber', wmdp_bio: 'WMDP Bio', wmdp_chem: 'WMDP Chem',
  bigcodebench: 'BigCodeBench', humaneval: 'HumanEval', mmlu: 'MMLU',
  gsm8k: 'GSM8K', hellaswag: 'HellaSWAG', gdm_dangerous_stealth: 'GDM Stealth',
}

const form = reactive({
  taskName: '',
  modelName: '',
  benchmarkSuite: '',
})

function suiteName(key) { return SUITE_LABELS[key] || key }

const statusLabel = (s) => {
  const map = { submitting:'提交中', submit_failed:'提交失败', pending:'排队中', running:'测评中', success:'已完成', failed:'失败', timeout:'超时', not_found:'任务丢失', query_error:'查询异常' }
  return map[s] || s
}
const statusTone = (s) => {
  const map = { submitting:'progress', submit_failed:'danger', pending:'neutral', running:'progress', success:'success', failed:'danger', timeout:'warning', not_found:'warning', query_error:'neutral' }
  return map[s] || 'neutral'
}
const dbStatusLabel = (s) => {
  const map = { pending:'排队中', running:'测评中', success:'已完成', failed:'失败' }
  return map[s] || s
}
const dbStatusTone = (s) => {
  const map = { pending:'neutral', running:'progress', success:'success', failed:'danger' }
  return map[s] || 'neutral'
}
function formatTime(iso) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }
function openTaskLogs(row) { taskLogDialogRef.value?.open(row) }
function canOpenTaskLogs(task) { return !['submitting', 'submit_failed'].includes(task.frontendStatus) }

function closeDialog() {
  showDialog.value = false
  selectedModelId.value = null
  Object.assign(form, { taskName: '', modelName: '', benchmarkSuite: '' })
}

async function fetchModelPresets() {
  try {
    const { data } = await listModels(1, 200, false)
    modelPresets.value = data.data.items
  } catch { /* non-critical */ }
}

function applyModelPreset(id) {
  const m = modelPresets.value.find(x => x.id === id)
  if (!m) return
  form.modelName = m.model_name
}

async function fetchHistoryTasks() {
  tableLoading.value = true
  try {
    const { data } = await listBenchmarks(page.value, perPage)
    historyTasks.value = data.data.items
    total.value = data.data.total
  } catch { /* ignore */ } finally {
    tableLoading.value = false
  }
}

async function retryDbTask(row) {
  try {
    const { data } = await retryBenchmark(row.id)
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    const newId = data.data.id
    activeTasks.value.unshift({ ...data.data, id: newId, frontendStatus: 'pending', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null })
    startPolling(newId)
    ElMessage.success('已重新提交')
  } catch (err) {
    ElMessage.error('重试失败：' + (err.response?.data?.message || '网络异常'))
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该测评任务？删除后不可恢复。', '删除确认', {
      confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  try {
    await deleteBenchmark(row.id)
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    ElMessage.success('任务已删除')
  } catch (err) {
    ElMessage.error('删除失败：' + (err.response?.data?.message || '网络异常'))
  }
}

function _updateActiveTask(taskId, updates) {
  const idx = activeTasks.value.findIndex(t => t.id === taskId)
  if (idx !== -1) Object.assign(activeTasks.value[idx], updates)
}
function _getActiveTask(taskId) { return activeTasks.value.find(t => t.id === taskId) }

async function handleSubmit() {
  if (!form.taskName.trim()) return ElMessage.warning('请填写任务名称')
  if (!form.modelName.trim()) return ElMessage.warning('请从模型库选择被测模型')
  if (!form.benchmarkSuite) return ElMessage.warning('请选择 Benchmark')

  const payload = {
    task_name: form.taskName.trim(),
    model_name: form.modelName.trim(),
    benchmark_suite: form.benchmarkSuite,
    benchmark_config: null,
  }

  closeDialog()
  const tempId = Date.now()
  activeTasks.value.unshift({ id: tempId, task_name: payload.task_name, model_name: payload.model_name, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null })
  submitting.value = true

  try {
    const { data } = await submitBenchmark(payload)
    _updateActiveTask(tempId, { id: data.data.id, ...data.data, frontendStatus: 'pending' })
    startPolling(data.data.id)
    ElMessage.success('测评任务已提交')
  } catch (err) {
    _updateActiveTask(tempId, { frontendStatus: 'submit_failed', error: err.response?.data?.message || '提交失败' })
  } finally {
    submitting.value = false
  }
}

function startPolling(taskId) {
  stopPolling(taskId)
  _updateActiveTask(taskId, { pollCount: 0 })
  const task = _getActiveTask(taskId)
  if (!task) return

  task.elapsedTimer = setInterval(() => {
    const t = _getActiveTask(taskId)
    if (t) t.elapsed++
  }, 1000)

  task.pollTimer = setInterval(async () => {
    const t = _getActiveTask(taskId)
    if (!t) { stopPolling(taskId); return }
    _updateActiveTask(taskId, { pollCount: t.pollCount + 1 })
    try {
      const { data } = await getBenchmark(t.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        stopPolling(taskId)
        activeTasks.value = activeTasks.value.filter(x => x.id !== taskId)
        historyTasks.value.unshift(data.data)
        total.value++
        if (s === 'success') ElMessage.success('测评完成')
      } else {
        _updateActiveTask(taskId, { frontendStatus: s })
      }
    } catch (err) {
      if (err.response?.status === 404) { _updateActiveTask(taskId, { frontendStatus: 'not_found' }); stopPolling(taskId) }
      else _updateActiveTask(taskId, { frontendStatus: 'query_error' })
    }
    const current = _getActiveTask(taskId)
    if (current && current.pollCount >= MAX_POLLS && !['success', 'failed'].includes(current.frontendStatus)) {
      stopPolling(taskId)
      if (current.frontendStatus !== 'not_found') _updateActiveTask(taskId, { frontendStatus: 'timeout' })
    }
  }, 2000)
}

function stopPolling(taskId) {
  const t = _getActiveTask(taskId)
  if (t) {
    clearInterval(t.pollTimer)
    clearInterval(t.elapsedTimer)
    t.pollTimer = null
    t.elapsedTimer = null
  }
}

onMounted(() => {
  fetchHistoryTasks()
  fetchModelPresets()
  if (route.query.action === 'new') showDialog.value = true
})
onUnmounted(() => activeTasks.value.forEach(t => {
  clearInterval(t.pollTimer)
  clearInterval(t.elapsedTimer)
}))
</script>
<style scoped>
.benchmark-task {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
}

.page-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
}

/* ─── 指标条 ─── */
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-7);
  padding: var(--space-7) var(--space-8);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
}
.metric { display: flex; flex-direction: column; gap: var(--space-3); }
.metric-value {
  font-size: var(--text-3xl);
  color: var(--fg-primary);
  font-weight: var(--weight-semibold);
}

/* ─── 任务区块 ─── */
.task-section { display: flex; flex-direction: column; gap: var(--space-6); }
.task-section__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

/* ─── 进行中卡片 ─── */
.active-list { display: flex; flex-direction: column; gap: var(--space-5); }
.active-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-7) var(--space-8);
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  transition: box-shadow var(--dur-base) var(--ease-out),
              border-color var(--dur-base) var(--ease-out);
}
.active-card:hover {
  box-shadow: var(--shadow-sm);
  border-color: var(--border-default);
}
.active-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-5);
}
.active-card__info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}
.active-card__name {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.active-card__model {
  color: var(--fg-tertiary);
  font-family: var(--font-mono);
}
.active-card__actions {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-shrink: 0;
}
.active-card__meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  color: var(--fg-secondary);
}

/* ─── 状态徽章 ─── */
.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-5);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.02em;
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
  border: 1px solid transparent;
  white-space: nowrap;
}
.status-pill[data-tone='success'] { background: var(--color-success-bg); color: var(--color-success-fg); border-color: var(--color-success-border); }
.status-pill[data-tone='warning'] { background: var(--color-warning-bg); color: var(--color-warning-fg); border-color: var(--color-warning-border); }
.status-pill[data-tone='danger']  { background: var(--color-danger-bg);  color: var(--color-danger-fg);  border-color: var(--color-danger-border); }
.status-pill[data-tone='progress']{ background: var(--color-info-bg);    color: var(--color-info-fg);    border-color: var(--color-info-border); }

/* ─── Suite 标签 ─── */
.suite-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-4);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  background: var(--state-selected);
  color: var(--fg-primary);
  border: 1px solid var(--border-subtle);
}

/* ─── 历史表格 ─── */
.history-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

/* ─── 展开行 ─── */
.expand-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-6);
  padding: var(--space-7) var(--space-8);
}
.settings-card {
  background: var(--bg-surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-6) var(--space-7);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.settings-card__label {
  margin: 0;
  color: var(--fg-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.info-dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-3) var(--space-6);
  margin: 0;
  align-items: baseline;
}
.info-dl dt {
  color: var(--fg-secondary);
  font-size: var(--text-xs);
  white-space: nowrap;
}
.info-dl dd {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--fg-primary);
  word-break: break-all;
}
.error-text { color: var(--color-danger-fg); }

.json-pre {
  margin: 0;
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--fg-secondary);
  background: var(--bg-canvas);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-4) var(--space-5);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.result-card { grid-column: 1 / -1; }

.result-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) 0;
  color: var(--fg-tertiary);
}
.result-placeholder__icon {
  font-size: 32px;
  color: var(--border-default);
}

/* ─── 分页 ─── */
.pagination { margin-top: var(--space-6); justify-content: center; }

/* ─── 空状态 ─── */
.empty-state {
  background: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-12) var(--space-9);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-5);
}
.empty-state__title {
  margin: 0;
  font-size: var(--text-2xl);
  color: var(--fg-primary);
}
.empty-state__lede {
  margin: 0;
  color: var(--fg-secondary);
  max-width: 48ch;
}
.empty-state .el-button { margin-top: var(--space-3); }

@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
  .expand-grid { grid-template-columns: 1fr; }
}
</style>

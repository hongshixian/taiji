<template>
  <div class="page-shell model-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">资源 · 模型库</span>
      <div class="page-header__row">
        <h1 class="page-header__title">模型管理</h1>
        <el-button type="primary" @click="openCreateDialog" v-if="has('model:write')">
          <el-icon><Plus /></el-icon>&nbsp;添加模型
        </el-button>
      </div>
      <p class="page-header__lede">
        配置被测模型的 API 信息，供测评任务直接调用。数据归属当前租户，其他租户不可见。
      </p>
    </header>

    <section v-if="loading || models.length" class="data-section">
      <div class="section-toolbar">
        <label class="toolbar-switch">
          <el-switch v-model="showInactive" @change="handleFilterChange" />
          <span class="t-caption">显示已停用</span>
        </label>
      </div>

      <el-table :data="models" stripe v-loading="loading" class="data-table" data-density="compact">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="显示名称" min-width="160">
          <template #default="{ row }">
            <span class="model-name">{{ row.display_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="模型标识" min-width="160">
          <template #default="{ row }">
            <span class="t-mono">{{ row.model_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="协议" width="110">
          <template #default="{ row }">
            <span class="proto-badge">{{ row.api_protocol }}</span>
          </template>
        </el-table-column>
        <el-table-column label="API 地址" min-width="220">
          <template #default="{ row }">
            <span class="t-mono url-cell">{{ row.api_base_url }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span class="t-mono">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button
              text type="primary" size="small"
              :loading="testingId === row.id"
              @click="handleTest(row)"
            >测试</el-button>
            <el-button
              v-if="has('model:write')"
              text type="primary" size="small"
              @click="openEditDialog(row)"
            >编辑</el-button>
            <el-button
              v-if="has('model:write')"
              text size="small"
              :type="row.is_active ? 'warning' : 'success'"
              @click="toggleActive(row)"
            >{{ row.is_active ? '停用' : '启用' }}</el-button>
            <el-button
              v-if="has('model:delete')"
              text type="danger" size="small"
              @click="handleDelete(row)"
            >删除</el-button>
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
        @current-change="fetchModels"
      />
    </section>

    <!-- 空状态 -->
    <section
      v-if="!loading && models.length === 0"
      class="empty-state"
    >
      <span class="t-eyebrow">暂无模型</span>
      <h3 class="empty-state__title">还没有配置任何模型</h3>
      <p class="empty-state__lede">
        在这里维护被测模型的 API 地址、密钥等信息，创建测评任务时可直接从模型库选择，无需重复填写。
      </p>
      <el-button v-if="has('model:write')" type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>&nbsp;添加第一个模型
      </el-button>
    </section>

    <!-- 新建 / 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editMode ? '编辑模型配置' : '添加模型'"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form label-width="100px" @submit.prevent>
        <el-form-item label="显示名称" required>
          <el-input
            v-model="form.display_name"
            placeholder="例：GPT-4o（OpenAI 官方）"
            maxlength="100"
            show-word-limit
          />
          <div class="form-hint">显示在测评榜单和任务列表中的名称</div>
        </el-form-item>
        <el-form-item label="模型标识" required>
          <el-input
            v-model="form.model_name"
            placeholder="例：gpt-4o"
            maxlength="200"
            class="mono-input"
          />
          <div class="form-hint">API 请求 body 中的 model 字段值</div>
        </el-form-item>
        <el-form-item label="API 协议" required>
          <el-select v-model="form.api_protocol" style="width:100%">
            <el-option label="OpenAI 兼容" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="Gemini" value="gemini" />
            <el-option label="Ollama" value="ollama" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="API 地址" required>
          <el-input
            v-model="form.api_base_url"
            placeholder="https://api.openai.com/v1"
            maxlength="500"
            class="mono-input"
          />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="editMode ? '留空则不修改原有密钥' : 'sk-...（可选，加密存储）'"
            maxlength="500"
            class="mono-input"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="可选的备注说明"
            maxlength="500"
          />
        </el-form-item>

        <el-divider content-position="left">生成参数</el-divider>
        <p class="form-hint form-hint--block">
          评测时将统一使用这里配置的采样参数，保证同一模型的结果可比。留空则由引擎使用默认值。
        </p>
        <div class="gen-grid">
          <el-form-item label="Temperature">
            <el-input-number
              v-model="form.gen_temperature"
              :min="0" :max="2" :step="0.1" :precision="2"
              controls-position="right"
              placeholder="可选"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item label="Top-P">
            <el-input-number
              v-model="form.gen_top_p"
              :min="0" :max="1" :step="0.05" :precision="2"
              controls-position="right"
              placeholder="可选"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item label="Max Tokens">
            <el-input-number
              v-model="form.gen_max_tokens"
              :min="1" :max="200000" :step="256"
              controls-position="right"
              placeholder="可选"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item label="Stop 序列">
            <el-input
              v-model="form.gen_stop_sequences"
              placeholder="逗号分隔，可选"
            />
          </el-form-item>
        </div>

        <el-form-item v-if="editMode" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editMode ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试结果对话框 -->
    <el-dialog
      v-model="testDialogVisible"
      title="模型连通性测试"
      width="600px"
      :close-on-click-modal="false"
    >
      <div v-if="testResult" class="test-result">
        <div class="test-result__header">
          <span
            class="status-pill"
            :data-tone="testResult.ok ? 'success' : 'danger'"
          >
            {{ testResult.ok ? '通过' : '失败' }}
          </span>
          <span class="t-caption">模型：{{ testTargetName }}</span>
        </div>
        <div class="test-result__grid">
          <div class="test-result__item">
            <span class="t-eyebrow">耗时</span>
            <span class="t-mono">{{ testResult.latency_ms }} ms</span>
          </div>
          <div class="test-result__item">
            <span class="t-eyebrow">Provider</span>
            <span class="t-mono">{{ testResult.provider }}</span>
          </div>
          <div class="test-result__item">
            <span class="t-eyebrow">Model</span>
            <span class="t-mono">{{ testResult.model }}</span>
          </div>
        </div>
        <div v-if="testResult.ok" class="test-result__block">
          <div class="t-eyebrow">样例输出</div>
          <pre class="test-result__text">{{ testResult.sample_output || '(空)' }}</pre>
        </div>
        <div v-else class="test-result__block">
          <div class="t-eyebrow">错误信息</div>
          <pre class="test-result__text test-result__text--error">{{ testResult.error }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listModels, createModel, updateModel, deleteModel, testModel } from '../api/model'
import { usePermission } from '../composables/usePermission'

const { has } = usePermission()

const models = ref([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)
const showInactive = ref(false)

const dialogVisible = ref(false)
const editMode = ref(false)
const editId = ref(null)
const submitting = ref(false)

// 测试相关
const testingId = ref(null)
const testDialogVisible = ref(false)
const testResult = ref(null)
const testTargetName = ref('')

const form = reactive({
  display_name: '',
  model_name: '',
  api_protocol: 'openai',
  api_base_url: '',
  api_key: '',
  description: '',
  is_active: true,
  gen_temperature: null,
  gen_top_p: null,
  gen_max_tokens: null,
  gen_stop_sequences: '',
})

function formatTime(iso) {
  return iso ? new Date(iso).toLocaleString('zh-CN') : '—'
}

function resetForm() {
  editMode.value = false
  editId.value = null
  Object.assign(form, {
    display_name: '',
    model_name: '',
    api_protocol: 'openai',
    api_base_url: '',
    api_key: '',
    description: '',
    is_active: true,
    gen_temperature: null,
    gen_top_p: null,
    gen_max_tokens: null,
    gen_stop_sequences: '',
  })
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  resetForm()
  editMode.value = true
  editId.value = row.id
  const extra = row.extra_params || {}
  const stops = extra.stop_sequences || extra.stop_seqs
  Object.assign(form, {
    display_name: row.display_name,
    model_name: row.model_name,
    api_protocol: row.api_protocol,
    api_base_url: row.api_base_url,
    api_key: '',   // never pre-fill — backend masks it
    description: row.description || '',
    is_active: row.is_active,
    gen_temperature: extra.temperature ?? null,
    gen_top_p: extra.top_p ?? null,
    gen_max_tokens: extra.max_tokens ?? null,
    gen_stop_sequences: Array.isArray(stops) ? stops.join(', ') : (stops || ''),
  })
  dialogVisible.value = true
}

async function fetchModels() {
  loading.value = true
  try {
    const { data } = await listModels(page.value, perPage, showInactive.value)
    models.value = data.data.items
    total.value = data.data.total
  } catch {
    ElMessage.error('加载模型列表失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  page.value = 1
  fetchModels()
}

async function handleSubmit() {
  if (!form.display_name.trim()) return ElMessage.warning('请填写显示名称')
  if (!form.model_name.trim()) return ElMessage.warning('请填写模型标识')
  if (!form.api_base_url.trim()) return ElMessage.warning('请填写 API 地址')

  submitting.value = true
  try {
    // 装配 extra_params
    const extra = {}
    if (form.gen_temperature !== null && form.gen_temperature !== undefined) {
      extra.temperature = form.gen_temperature
    }
    if (form.gen_top_p !== null && form.gen_top_p !== undefined) {
      extra.top_p = form.gen_top_p
    }
    if (form.gen_max_tokens !== null && form.gen_max_tokens !== undefined) {
      extra.max_tokens = form.gen_max_tokens
    }
    const stops = (form.gen_stop_sequences || '').split(',').map((s) => s.trim()).filter(Boolean)
    if (stops.length) extra.stop_sequences = stops

    const payload = {
      display_name: form.display_name.trim(),
      model_name: form.model_name.trim(),
      api_protocol: form.api_protocol,
      api_base_url: form.api_base_url.trim(),
      description: form.description.trim() || null,
      extra_params: extra,
    }
    if (form.api_key.trim()) {
      payload.api_key = form.api_key.trim()
    }
    if (editMode.value) {
      payload.is_active = form.is_active
      await updateModel(editId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createModel(payload)
      ElMessage.success('模型已添加')
    }
    dialogVisible.value = false
    page.value = 1
    await fetchModels()
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row) {
  try {
    await updateModel(row.id, { is_active: !row.is_active })
    row.is_active = !row.is_active
    ElMessage.success(row.is_active ? '已启用' : '已停用')
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  }
}

async function handleTest(row) {
  testingId.value = row.id
  testTargetName.value = row.display_name
  try {
    const { data } = await testModel(row.id)
    testResult.value = data.data
    testDialogVisible.value = true
    if (testResult.value.ok) {
      ElMessage.success(`测试通过（${testResult.value.latency_ms}ms）`)
    } else {
      ElMessage.warning('测试失败，请查看错误详情')
    }
  } catch (err) {
    testResult.value = {
      ok: false,
      latency_ms: 0,
      sample_output: null,
      error: err.response?.data?.message || err.message || '请求失败',
      provider: row.api_protocol,
      model: row.model_name,
    }
    testDialogVisible.value = true
    ElMessage.error(err.response?.data?.message || '测试请求失败')
  } finally {
    testingId.value = null
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除模型「${row.display_name}」？删除后不可恢复，已关联该模型的历史任务不受影响。`,
      '删除确认',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await deleteModel(row.id)
    models.value = models.value.filter(m => m.id !== row.id)
    total.value--
    ElMessage.success('已删除')
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '删除失败')
  }
}

onMounted(fetchModels)
</script>

<style scoped>
.model-management {
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

/* ─── 数据区块 ─── */
.data-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  padding: var(--space-7) var(--space-8);
}

.section-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.toolbar-switch {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  cursor: pointer;
}

/* ─── 表格 ─── */
.data-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.model-name {
  font-weight: var(--weight-medium);
  color: var(--fg-primary);
}

.url-cell {
  font-size: var(--text-xs);
  color: var(--fg-secondary);
  word-break: break-all;
}

/* ─── 协议标签 ─── */
.proto-badge {
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
.status-pill[data-tone='danger']  { background: var(--color-danger-bg);  color: var(--color-danger-fg);  border-color: var(--color-danger-border); }

/* ─── 表单提示 ─── */
.form-hint {
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
  margin-top: var(--space-2);
  line-height: 1.4;
}
.form-hint--block {
  margin: 0 0 var(--space-5);
}

/* ─── 生成参数栅格 ─── */
.gen-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 var(--space-6);
}
@media (max-width: 560px) {
  .gen-grid { grid-template-columns: 1fr; }
}

.mono-input :deep(input),
.mono-input :deep(textarea) {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

/* ─── 分页 ─── */
.pagination {
  margin-top: var(--space-4);
  justify-content: center;
}

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

/* ─── 测试结果对话框 ─── */
.test-result {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.test-result__header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.test-result__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--bg-canvas);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}
.test-result__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.test-result__block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.test-result__text {
  margin: 0;
  padding: var(--space-4);
  background: var(--bg-canvas);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow: auto;
}
.test-result__text--error {
  color: var(--color-danger-fg, #c94040);
  background: var(--color-danger-bg, #fdecec);
  border-color: var(--color-danger-border, #f5b8b8);
}

@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
}
</style>

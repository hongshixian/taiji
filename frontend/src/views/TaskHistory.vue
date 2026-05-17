<template>
  <div class="task-history">
    <h1>历史任务</h1>

    <el-table :data="tasks" v-loading="loading" stripe class="history-table">
      <el-table-column label="URL" min-width="300">
        <template #default="{ row }">
          <a :href="row.url" target="_blank" class="url-link">{{ row.url }}</a>
        </template>
      </el-table-column>
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          {{ row.title || '—' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button text type="primary" @click="viewDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-if="total > perPage"
      v-model:current-page="page"
      :page-size="perPage"
      :total="total"
      layout="prev, pager, next"
      class="pagination"
      @current-change="fetchTasks"
    />

    <!-- 详情弹窗 -->
    <el-dialog v-model="dialogVisible" title="任务详情" width="600px">
      <template v-if="detailTask">
        <div class="detail-item">
          <strong>URL：</strong>
          <a :href="detailTask.url" target="_blank">{{ detailTask.url }}</a>
        </div>
        <div class="detail-item">
          <strong>状态：</strong>
          <el-tag :type="statusTag(detailTask.status)">{{ statusLabel(detailTask.status) }}</el-tag>
        </div>
        <div v-if="detailTask.status === 'success'" class="detail-item">
          <strong>标题：</strong>{{ detailTask.title }}
        </div>
        <div v-if="detailTask.status === 'success'" class="detail-item">
          <strong>摘要：</strong>
          <p class="detail-summary">{{ detailTask.summary }}</p>
        </div>
        <div v-if="detailTask.keywords?.length" class="detail-item">
          <strong>关键词：</strong>
          <el-tag v-for="k in detailTask.keywords" :key="k" size="small" class="kw-tag">{{ k }}</el-tag>
        </div>
        <div v-if="detailTask.status === 'failed'" class="detail-item">
          <strong>错误信息：</strong>
          <el-alert :description="detailTask.error_message" type="error" />
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listAnalyses } from '../api/analyze'

const tasks = ref([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)

const dialogVisible = ref(false)
const detailTask = ref(null)

function statusLabel(status) {
  const map = { pending: '排队中', running: '分析中', success: '已完成', failed: '失败' }
  return map[status] || status
}

function statusTag(status) {
  const map = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[status] || 'info'
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchTasks() {
  loading.value = true
  try {
    const { data } = await listAnalyses(page.value, perPage)
    tasks.value = data.data.items
    total.value = data.data.total
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

function viewDetail(task) {
  detailTask.value = task
  dialogVisible.value = true
}

onMounted(fetchTasks)
</script>

<style scoped>
.task-history {
  padding: 40px;
  max-width: 1000px;
  margin: 0 auto;
}
h1 {
  margin-bottom: 24px;
}
.history-table {
  width: 100%;
}
.url-link {
  color: #409eff;
  text-decoration: none;
  word-break: break-all;
}
.pagination {
  margin-top: 20px;
  justify-content: center;
}
.detail-item {
  margin-bottom: 12px;
}
.detail-summary {
  color: #606266;
  line-height: 1.6;
  margin-top: 4px;
}
.kw-tag {
  margin-right: 4px;
}
</style>
<template>
  <div class="home">
    <h2>欢迎回来，{{ authStore.user?.username }}</h2>
    <p class="welcome-text">太极网页分析平台，快速提取网页的标题、摘要和关键词。</p>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总任务数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card success-card">
          <div class="stat-value">{{ stats.success }}</div>
          <div class="stat-label">已完成</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card warning-card">
          <div class="stat-value">{{ stats.pending }}</div>
          <div class="stat-label">进行中</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { listAnalyses } from '../api/analyze'

const authStore = useAuthStore()
const stats = ref({ total: 0, success: 0, pending: 0 })

onMounted(async () => {
  try {
    const { data } = await listAnalyses(1, 1000)
    const items = data.data.items
    stats.value.total = data.data.total
    stats.value.success = items.filter((i) => i.status === 'success').length
    stats.value.pending = data.data.total - stats.value.success
  } catch {
    // ignore
  }
})
</script>

<style scoped>
.home {
  max-width: 900px;
}
h2 {
  margin-bottom: 8px;
}
.welcome-text {
  color: #909399;
  margin-bottom: 32px;
}
.stats-row {
  margin-bottom: 24px;
}
.stat-card {
  text-align: center;
  padding: 8px 0;
}
.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #303133;
}
.stat-label {
  color: #909399;
  margin-top: 4px;
  font-size: 14px;
}
.success-card .stat-value { color: #67c23a; }
.warning-card .stat-value { color: #e6a23c; }
</style>

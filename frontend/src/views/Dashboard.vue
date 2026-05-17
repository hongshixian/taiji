<template>
  <div class="dashboard">
    <h1>太极 · 网页分析</h1>
    <p class="subtitle">输入一个 URL，异步分析网页内容（Phase 5 实现）</p>
    <el-input
      v-model="url"
      placeholder="请输入网页 URL，例如 https://example.com"
      size="large"
      disabled
      style="max-width: 600px; margin-top: 30px;"
    />
    <p style="margin-top: 20px; color: #909399;">
      分析功能即将上线，当前为占位页面
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const url = ref('')
</script>

<style scoped>
.dashboard {
  padding: 40px;
}
h1 {
  margin-bottom: 8px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
}
</style>
<template>
  <div class="settings">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Tools /></el-icon>
        <h2>通用设置</h2>
      </div>
    </div>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <div class="card-title">
          <el-icon><Brush /></el-icon>&nbsp;外观
        </div>
      </template>
      <div class="setting-item">
        <div>
          <div class="item-label">主题模式</div>
          <div class="item-desc">切换浅色 / 深色界面</div>
        </div>
        <el-switch
          v-model="isDark"
          :active-action-icon="Moon"
          :inactive-action-icon="Sunny"
          @change="toggleTheme"
        />
      </div>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <div class="card-title">
          <el-icon><InfoFilled /></el-icon>&nbsp;关于
        </div>
      </template>
      <div class="about-grid">
        <div><span class="about-label">项目</span><span class="about-value">太极 Taiji</span></div>
        <div><span class="about-label">版本</span><span class="about-value">v0.1.0</span></div>
        <div><span class="about-label">技术栈</span><span class="about-value">Flask 3 + Vue 3 + Celery + Redis</span></div>
        <div><span class="about-label">开源协议</span><span class="about-value">MIT License</span></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, shallowRef } from 'vue'
import { Moon, Sunny } from '@element-plus/icons-vue'

const isDark = ref(document.documentElement.classList.contains('dark'))

function toggleTheme(value) {
  document.documentElement.classList.toggle('dark', value)
  localStorage.setItem('taiji-theme', value ? 'dark' : 'light')
}
</script>

<style scoped>
.settings { max-width: 800px; margin: 0 auto; }
.top-bar { margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }
.settings-card {
  border: 1px solid var(--el-border-color-lighter);
  margin-bottom: 20px;
}
.card-title {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}
.item-label {
  font-size: 14px;
  color: var(--el-text-color-primary);
  font-weight: 500;
}
.item-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.about-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}
.about-grid > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.about-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  letter-spacing: 1px;
}
.about-value {
  font-size: 14px;
  color: var(--el-text-color-primary);
  font-weight: 500;
}
@media (max-width: 600px) {
  .about-grid { grid-template-columns: 1fr; }
}
</style>

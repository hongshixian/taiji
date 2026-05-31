<template>
  <!-- 普通用户：只读显示当前租户 -->
  <el-tooltip
    v-if="!authStore.isSuperuser"
    :content="tooltipText"
    placement="bottom"
  >
    <div class="tenant-readonly">
      <el-icon class="tenant-icon"><OfficeBuilding /></el-icon>
      <span class="tenant-name">{{ currentName }}</span>
    </div>
  </el-tooltip>

  <!-- 超级管理员：下拉切换租户 -->
  <el-dropdown
    v-else
    trigger="click"
    placement="bottom-end"
    @command="handleSwitch"
    @visible-change="onDropdownToggle"
  >
    <div class="tenant-trigger" :class="{ 'is-switched': isSwitched }">
      <el-icon class="tenant-icon"><OfficeBuilding /></el-icon>
      <span class="tenant-name">{{ currentName }}</span>
      <el-tag v-if="currentPlan" size="small" :type="planTagType(currentPlan)" effect="plain" class="plan-tag">
        {{ currentPlan }}
      </el-tag>
      <el-icon class="caret"><ArrowDown /></el-icon>
    </div>
    <template #dropdown>
      <el-dropdown-menu class="tenant-menu">
        <el-dropdown-item disabled>
          <span class="menu-hint">切换操作租户（超管）</span>
        </el-dropdown-item>
        <el-dropdown-item v-if="isSwitched" command="__reset" divided>
          <el-icon><RefreshLeft /></el-icon>
          <span>切回我的租户</span>
        </el-dropdown-item>
        <el-dropdown-item
          v-for="t in tenants"
          :key="t.id"
          :command="t.id"
          :disabled="t.id === currentId"
          :divided="$index === 0"
        >
          <div class="tenant-item">
            <span class="ti-name">{{ t.name }}</span>
            <span class="ti-slug">{{ t.slug }}</span>
            <el-tag size="small" :type="planTagType(t.plan)" effect="plain">{{ t.plan }}</el-tag>
            <el-tag v-if="!t.is_active" size="small" type="info" effect="plain">已禁用</el-tag>
          </div>
        </el-dropdown-item>
        <el-dropdown-item v-if="loading" disabled>
          <span class="menu-hint">加载中…</span>
        </el-dropdown-item>
        <el-dropdown-item v-else-if="!tenants.length" disabled>
          <span class="menu-hint">暂无租户</span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { listTenants } from '../api/superadmin'

const authStore = useAuthStore()
const tenants = ref([])
const loading = ref(false)
const loaded = ref(false)

const currentId = computed(() => authStore.currentTenant?.id)
const currentName = computed(() => authStore.currentTenant?.name || '未知租户')
const currentSlug = computed(() => authStore.currentTenant?.slug || '')
const currentPlan = computed(() => {
  // plan 信息在 user_to_dict 没暴露，从 tenants 列表反查；未加载时拉空
  if (!loaded.value || !currentId.value) return ''
  return tenants.value.find((t) => t.id === currentId.value)?.plan || ''
})
const tooltipText = computed(() => {
  const slug = currentSlug.value
  return slug ? `当前租户：${currentName.value} (${slug})` : `当前租户：${currentName.value}`
})

const isSwitched = computed(() => {
  return authStore.originalTenantId != null
    && currentId.value != null
    && authStore.originalTenantId !== currentId.value
})

function planTagType(plan) {
  return { free: 'info', pro: 'warning', enterprise: 'danger' }[plan] || 'info'
}

async function onDropdownToggle(visible) {
  if (visible && !loaded.value && !loading.value) {
    await fetchTenants()
  }
}

async function fetchTenants() {
  loading.value = true
  try {
    const { data } = await listTenants()
    tenants.value = data.data || []
    loaded.value = true
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载租户失败')
  } finally {
    loading.value = false
  }
}

async function handleSwitch(command) {
  try {
    if (command === '__reset') {
      await authStore.resetTenant()
      ElMessage.success(`已切回租户「${authStore.currentTenant?.name}」`)
    } else {
      await authStore.switchTenant(command)
      ElMessage.success(`已切换到租户「${authStore.currentTenant?.name}」`)
    }
    // 触发当前路由刷新，让页面重新拉数据
    setTimeout(() => window.location.reload(), 300)
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '切换失败')
  }
}
</script>

<style scoped>
.tenant-readonly,
.tenant-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--taiji-radius-sm);
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-size: 13px;
  max-width: 260px;
}
.tenant-trigger {
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.tenant-trigger:hover {
  border-color: var(--taiji-accent);
  background: var(--el-color-primary-light-9);
}
.tenant-trigger.is-switched {
  border-color: var(--taiji-accent);
  background: var(--el-color-danger-light-9);
}
.tenant-icon {
  font-size: 16px;
  color: var(--taiji-accent);
}
.tenant-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}
.plan-tag {
  text-transform: uppercase;
  font-size: 10px;
}
.caret {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.tenant-menu .menu-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.tenant-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 220px;
}
.ti-name {
  font-weight: 500;
  flex: 1;
}
.ti-slug {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .tenant-name { max-width: 80px; }
  .plan-tag { display: none; }
}
</style>

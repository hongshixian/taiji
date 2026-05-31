<template>
  <div class="settings">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Tools /></el-icon>
        <h2>通用设置</h2>
      </div>
    </div>

    <!-- 外观 -->
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

    <!-- 安全 -->
    <el-card shadow="never" class="settings-card">
      <template #header>
        <div class="card-title">
          <el-icon><Lock /></el-icon>&nbsp;安全
        </div>
      </template>
      <div class="setting-item">
        <div>
          <div class="item-label">登录密码</div>
          <div class="item-desc">修改后需要重新登录</div>
        </div>
        <el-button type="primary" plain size="default" @click="pwdDialogVisible = true">
          修改密码
        </el-button>
      </div>
    </el-card>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="460px" :close-on-click-modal="false">
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="100px"
        size="default"
        @submit.prevent="handleChangePassword"
      >
        <el-form-item label="当前密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closePwdDialog">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 关于 -->
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
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { changePassword } from '../api/auth'

const authStore = useAuthStore()

// 主题
const isDark = ref(document.documentElement.classList.contains('dark'))

function toggleTheme(value) {
  document.documentElement.classList.toggle('dark', value)
  localStorage.setItem('taiji-theme', value ? 'dark' : 'light')
}

// 修改密码
const pwdDialogVisible = ref(false)
const pwdFormRef = ref(null)
const pwdSubmitting = ref(false)
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const pwdRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' },
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.newPassword) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

function closePwdDialog() {
  pwdDialogVisible.value = false
  pwdFormRef.value?.resetFields()
}

async function handleChangePassword() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return

  pwdSubmitting.value = true
  try {
    await changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    pwdDialogVisible.value = false
    ElMessage.success('密码已修改，即将退出登录')
    setTimeout(() => {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('originalTenantId')
      authStore.user = null
      authStore.isLoggedIn = false
      window.location.hash = '#/login'
    }, 1500)
  } catch (err) {
    const msg = err.response?.data?.message || '修改失败'
    ElMessage.error(msg)
  } finally {
    pwdSubmitting.value = false
  }
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

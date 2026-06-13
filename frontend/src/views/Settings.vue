<template>
  <div class="page-shell settings">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">个人 · 偏好</span>
      <h1 class="page-header__title">通用设置</h1>
      <p class="page-header__lede">
        外观、安全、关于。修改密码后会自动退出登录。
      </p>
    </header>

    <section class="settings-card">
      <header class="settings-card__header">
        <span class="t-eyebrow">外观</span>
        <h2 class="settings-card__title">主题</h2>
      </header>
      <div class="setting-row">
        <div class="setting-row__text">
          <div class="setting-row__label">主题模式</div>
          <div class="setting-row__desc">切换浅色 / 深色界面。系统设置会被本地偏好覆盖。</div>
        </div>
        <el-switch
          v-model="isDark"
          :active-action-icon="Moon"
          :inactive-action-icon="Sunny"
          @change="toggleTheme"
        />
      </div>
    </section>

    <section class="settings-card">
      <header class="settings-card__header">
        <span class="t-eyebrow">安全</span>
        <h2 class="settings-card__title">登录密码</h2>
      </header>
      <div class="setting-row">
        <div class="setting-row__text">
          <div class="setting-row__label">修改密码</div>
          <div class="setting-row__desc">修改后所有现有 token 立即失效，需要重新登录。</div>
        </div>
        <el-button type="primary" plain @click="pwdDialogVisible = true">
          修改密码
        </el-button>
      </div>
    </section>

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

    <section class="settings-card">
      <header class="settings-card__header">
        <span class="t-eyebrow">关于</span>
        <h2 class="settings-card__title">项目信息</h2>
      </header>
      <dl class="about-grid">
        <div>
          <dt class="t-eyebrow">项目</dt>
          <dd class="t-mono about-value">Taiji × Fangcun</dd>
        </div>
        <div>
          <dt class="t-eyebrow">版本</dt>
          <dd class="t-mono about-value">v0.1.0</dd>
        </div>
        <div>
          <dt class="t-eyebrow">技术栈</dt>
          <dd class="about-value">Flask 3 · Vue 3 · Celery · Redis</dd>
        </div>
        <div>
          <dt class="t-eyebrow">协议</dt>
          <dd class="about-value">MIT License</dd>
        </div>
      </dl>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { changePassword } from '../api/auth'
import { applyTheme, isDarkActive } from '../utils/theme'

const authStore = useAuthStore()

const isDark = ref(isDarkActive())

function toggleTheme(value) {
  applyTheme(value)
}

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
.settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
  max-width: 800px;
}

.settings-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
  box-shadow: var(--shadow-xs);
}
.settings-card__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.settings-card__title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
  letter-spacing: -0.01em;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
}
.setting-row__text { display: flex; flex-direction: column; gap: 2px; }
.setting-row__label {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
}
.setting-row__desc {
  font-size: var(--text-sm);
  color: var(--fg-secondary);
}

.about-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6) var(--space-9);
  margin: 0;
}
.about-grid > div {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.about-grid dt { letter-spacing: 0.18em; }
.about-grid dd {
  margin: 0;
  font-size: var(--text-md);
  color: var(--fg-primary);
  font-weight: var(--weight-medium);
}
.about-value { color: var(--fg-primary); }

@media (max-width: 600px) {
  .about-grid { grid-template-columns: 1fr; }
  .setting-row { flex-direction: column; align-items: flex-start; gap: var(--space-5); }
}
</style>

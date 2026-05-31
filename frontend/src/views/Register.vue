<template>
  <div class="auth-page">
    <div class="brand-side">
      <div class="brand-content">
        <img src="../assets/taiji-logo.svg" alt="taiji" class="brand-logo" />
        <h1 class="brand-title">太极</h1>
        <p class="brand-slogan">阴阳相生 · 万象归一</p>
        <p class="brand-desc">注册即可体验完整链路</p>
      </div>
      <div class="brand-decoration">
        <div class="circle circle-1"></div>
        <div class="circle circle-2"></div>
        <div class="circle circle-3"></div>
      </div>
    </div>

    <div class="form-side">
      <el-card class="auth-card" shadow="never">
        <h2 class="auth-title">创建账号</h2>
        <p class="auth-subtitle">加入太极开始使用</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          size="large"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="用户名（3-80 字符）">
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="email">
            <el-input v-model="form.email" placeholder="邮箱">
              <template #prefix><el-icon><Message /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码（至少 6 位）"
              show-password
            >
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              :loading="loading"
              class="auth-btn"
            >
              注 册
            </el-button>
          </el-form-item>
        </el-form>

        <div class="auth-footer">
          已有账号？<router-link to="/login">返回登录</router-link>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 80, message: '用户名长度 3-80 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.register(form.username, form.email, form.password)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (err) {
    const msg = err.response?.data?.message || '注册失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 复用 Login 页同款样式 */
.auth-page {
  display: flex;
  min-height: 100vh;
  background: var(--el-bg-color);
}
.brand-side {
  flex: 1.2;
  position: relative;
  background: var(--taiji-gradient-hero);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  overflow: hidden;
}
.brand-content {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 40px;
}
.brand-logo {
  width: 96px;
  height: 96px;
  filter: drop-shadow(0 4px 16px rgba(0, 0, 0, 0.3));
  animation: spin 24s linear infinite;
}
.brand-title {
  font-size: 56px;
  font-weight: 700;
  letter-spacing: 8px;
  margin: 16px 0 8px;
  background: linear-gradient(135deg, #fff 0%, #d4a017 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand-slogan { font-size: 16px; letter-spacing: 4px; opacity: 0.9; margin: 0 0 24px; }
.brand-desc { font-size: 13px; opacity: 0.6; letter-spacing: 1px; }
.brand-decoration { position: absolute; inset: 0; pointer-events: none; }
.circle { position: absolute; border-radius: 50%; border: 1px solid rgba(255, 255, 255, 0.1); }
.circle-1 { width: 480px; height: 480px; top: -120px; right: -120px; }
.circle-2 { width: 320px; height: 320px; bottom: -80px; left: -80px; }
.circle-3 { width: 200px; height: 200px; top: 50%; left: 60%; opacity: 0.5; }

.form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.auth-card { width: 100%; max-width: 380px; border: none; background: transparent; }
.auth-card :deep(.el-card__body) { padding: 0; }
.auth-title { font-size: 28px; font-weight: 600; margin: 0 0 8px; color: var(--el-text-color-primary); }
.auth-subtitle { font-size: 14px; color: var(--el-text-color-secondary); margin: 0 0 32px; }
.auth-btn { width: 100%; letter-spacing: 4px; font-weight: 500; }
.auth-footer { text-align: center; margin-top: 16px; font-size: 14px; color: var(--el-text-color-secondary); }
.auth-footer a { color: var(--taiji-accent); text-decoration: none; font-weight: 500; margin-left: 4px; }
.auth-footer a:hover { text-decoration: underline; }

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .brand-side { display: none; }
  .form-side { flex: 1; }
}
</style>

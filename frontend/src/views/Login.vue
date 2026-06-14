<template>
  <div class="auth-page">
    <!-- 品牌区 — 暗色 marketing tier -->
    <aside class="brand-side fc-grain">
      <div class="brand-content">
        <span class="t-eyebrow brand-eyebrow">FANGCUN AI</span>
        <h1 class="brand-title fc-display-serif">
          为每一次推理，<br>
          构建可验证的<em class="fc-italic-word">边界</em>。
        </h1>
        <p class="brand-lede">
          多租户、JWT 吊销、SSRF 防护、审计日志。任务驱动的全栈骨架。
        </p>

        <dl class="brand-stats">
          <div>
            <dt class="t-eyebrow">DELIVERY</dt>
            <dd class="t-mono">docker compose up</dd>
          </div>
          <div>
            <dt class="t-eyebrow">RUNTIME</dt>
            <dd class="t-mono">Flask 3 · Vue 3 · Celery</dd>
          </div>
        </dl>

        <span class="brand-divider" aria-hidden="true"></span>
      </div>
    </aside>

    <!-- 表单区 — 亮色产品 UI -->
    <main class="form-side">
      <div class="form-shell">
        <header class="form-header">
          <span class="t-eyebrow">登录</span>
          <h2 class="form-title">欢迎回来</h2>
          <p class="form-lede">输入账号密码进入工作台。</p>
        </header>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          size="large"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              autocomplete="username"
            >
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              show-password
              autocomplete="current-password"
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
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <p class="form-footer">
          还没有账号？<router-link to="/register">注册账号</router-link>
        </p>
      </div>
    </main>
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
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const payload = { username: form.username, password: form.password }
    await authStore.login(payload)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (err) {
    const msg = err.response?.data?.message || '登录失败，请检查账号密码'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-canvas);
}

/* ─── 品牌区 — 暗色 hero ─── */
.brand-side {
  flex: 1.1;
  position: relative;
  background: var(--ink-950);
  color: var(--fg-inverse);
  display: flex;
  align-items: center;
  padding: var(--space-13) var(--space-12);
  overflow: hidden;
}
.brand-side::before {
  /* 紫色径向辉光，呼应 logo 渐变 */
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 25% 20%, rgba(143, 114, 208, 0.25) 0%, transparent 55%);
  z-index: 0;
}
.brand-content {
  position: relative;
  z-index: 2;
  max-width: 520px;
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
}
.brand-eyebrow {
  color: rgba(245, 240, 255, 0.55);
  letter-spacing: 0.22em;
}
.brand-title {
  font-size: clamp(40px, 5vw, 64px);
  line-height: 1.05;
  margin: 0;
  color: #f5f0ff;
  letter-spacing: -0.01em;
}
.brand-title em {
  color: #c9b37e;
  font-style: italic;
  font-weight: 400;
}
.brand-lede {
  font-size: var(--text-lg);
  line-height: var(--leading-relaxed);
  color: rgba(245, 240, 255, 0.72);
  margin: 0;
  max-width: 44ch;
}
.brand-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-8);
  margin: var(--space-7) 0 0;
  padding-top: var(--space-7);
  border-top: 1px solid rgba(245, 240, 255, 0.12);
}
.brand-stats dt {
  color: rgba(245, 240, 255, 0.55);
  letter-spacing: 0.18em;
  margin-bottom: var(--space-3);
}
.brand-stats dd {
  margin: 0;
  font-size: var(--text-md);
  color: #f5f0ff;
}
.brand-divider {
  width: 48px;
  height: 1px;
  background: #c9b37e;
  margin-top: var(--space-5);
}

/* ─── 表单区 — 亮色 ─── */
.form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-11) var(--space-9);
  background: var(--bg-surface);
}
.form-shell {
  width: 100%;
  max-width: 380px;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.form-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.form-title {
  font-size: var(--text-3xl);
  font-weight: var(--weight-bold);
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--fg-primary);
}
.form-lede {
  margin: 0;
  font-size: var(--text-md);
  color: var(--fg-secondary);
}
.auth-btn {
  width: 100%;
  font-weight: var(--weight-semibold);
  letter-spacing: 0.04em;
}
.form-footer {
  font-size: var(--text-sm);
  color: var(--fg-secondary);
  text-align: center;
  margin: 0;
}
.form-footer a {
  color: var(--violet-600);
  text-decoration: none;
  font-weight: var(--weight-semibold);
  margin-left: 4px;
}
.form-footer a:hover { text-decoration: underline; }

/* ─── 响应式 ─── */
@media (max-width: 900px) {
  .brand-side { display: none; }
}
</style>

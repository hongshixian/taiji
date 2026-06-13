<template>
  <div class="auth-page">
    <aside class="brand-side fc-grain">
      <div class="brand-content">
        <span class="t-eyebrow brand-eyebrow">FANGCUN · TAIJI</span>
        <h1 class="brand-title fc-display-serif">
          注册账号，<br>
          开始你的<em class="fc-italic-word">第一次</em>提交。
        </h1>
        <p class="brand-lede">
          注册后默认进入访客租户。任何时候都可以由超管把你加进其他租户。
        </p>

        <ol class="brand-steps">
          <li>
            <span class="step-num t-mono">01</span>
            <span class="step-text">填写用户名 / 邮箱 / 密码</span>
          </li>
          <li>
            <span class="step-num t-mono">02</span>
            <span class="step-text">登录后提交一个网页分析任务</span>
          </li>
          <li>
            <span class="step-num t-mono">03</span>
            <span class="step-text">在审计日志里查看自己的操作记录</span>
          </li>
        </ol>

        <span class="brand-divider" aria-hidden="true"></span>
      </div>
    </aside>

    <main class="form-side">
      <div class="form-shell">
        <header class="form-header">
          <span class="t-eyebrow">注册</span>
          <h2 class="form-title">创建账号</h2>
          <p class="form-lede">用户名长度 3 至 80 字符，密码至少 6 位。</p>
        </header>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          size="large"
          @submit.prevent="handleRegister"
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
          <el-form-item prop="email">
            <el-input
              v-model="form.email"
              placeholder="邮箱"
              autocomplete="email"
            >
              <template #prefix><el-icon><Message /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              show-password
              autocomplete="new-password"
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
              注册
            </el-button>
          </el-form-item>
        </el-form>

        <p class="form-footer">
          已有账号？<router-link to="/login">返回登录</router-link>
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
  email: '',
  password: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 80, message: '用户名长度 3 至 80 字符', trigger: 'blur' },
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
    const msg = err.response?.data?.message || '注册失败，请稍后重试'
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
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 75% 30%, rgba(143, 114, 208, 0.22) 0%, transparent 55%);
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
.brand-steps {
  list-style: none;
  margin: var(--space-7) 0 0;
  padding: var(--space-7) 0 0;
  border-top: 1px solid rgba(245, 240, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.brand-steps li {
  display: flex;
  align-items: baseline;
  gap: var(--space-6);
}
.step-num {
  color: #c9b37e;
  font-size: var(--text-lg);
  letter-spacing: 0.04em;
  flex-shrink: 0;
}
.step-text {
  color: rgba(245, 240, 255, 0.78);
  font-size: var(--text-md);
  line-height: var(--leading-relaxed);
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

@media (max-width: 900px) {
  .brand-side { display: none; }
}
</style>

<template>
  <div class="flex min-h-screen bg-canvas">
    <!-- 品牌区 — 暗色 marketing tier -->
    <aside class="relative hidden flex-[1.1] items-center overflow-hidden bg-[#0a0a14] px-16 py-20 text-fg-inverse lg:flex">
      <div
        class="pointer-events-none absolute inset-0 z-0"
        style="background: radial-gradient(circle at 75% 30%, rgba(143,114,208,0.22) 0%, transparent 55%)"
      />
      <div class="relative z-10 flex max-w-[520px] flex-col gap-8">
        <span class="text-2xs font-bold uppercase tracking-[0.22em] text-white/55">FANGCUN AI</span>
        <h1 class="m-0 text-5xl font-black leading-[1.05] tracking-tight text-[#f5f0ff]">
          注册账号，<br />
          开始你的<em class="font-normal italic text-[#c9b37e]">第一次</em>提交。
        </h1>
        <p class="m-0 max-w-[44ch] text-lg leading-relaxed text-white/70">
          注册后默认进入访客租户。任何时候都可以由超管把你加进其他租户。
        </p>

        <ol class="mt-4 flex list-none flex-col gap-5 border-t border-white/10 pt-6">
          <li class="flex items-baseline gap-6">
            <span class="shrink-0 font-mono text-lg tracking-wide text-[#c9b37e]">01</span>
            <span class="text-sm leading-relaxed text-white/75">填写用户名 / 邮箱 / 密码</span>
          </li>
          <li class="flex items-baseline gap-6">
            <span class="shrink-0 font-mono text-lg tracking-wide text-[#c9b37e]">02</span>
            <span class="text-sm leading-relaxed text-white/75">配置被测模型，提交一个 Benchmark 测评</span>
          </li>
          <li class="flex items-baseline gap-6">
            <span class="shrink-0 font-mono text-lg tracking-wide text-[#c9b37e]">03</span>
            <span class="text-sm leading-relaxed text-white/75">查看评测结果与排行榜</span>
          </li>
        </ol>

        <span class="mt-3 h-px w-12 bg-[#c9b37e]" />
      </div>
    </aside>

    <!-- 表单区 — 亮色产品 UI -->
    <main class="flex flex-1 items-center justify-center bg-surface px-8 py-16">
      <div class="flex w-full max-w-[380px] flex-col gap-8">
        <header class="flex flex-col gap-2">
          <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">注册</span>
          <h2 class="m-0 text-3xl font-bold tracking-tight text-fg">创建账号</h2>
          <p class="m-0 text-sm text-fg-secondary">用户名长度 3 至 80 字符，密码至少 6 位。</p>
        </header>

        <form class="flex flex-col gap-4" @submit.prevent="handleRegister">
          <div class="flex flex-col gap-1.5">
            <UiInput
              v-model="form.username"
              placeholder="用户名"
              autocomplete="username"
              @enter="handleRegister"
            >
              <template #prefix><User class="size-4" /></template>
            </UiInput>
            <p v-if="errors.username" class="text-xs text-danger">{{ errors.username }}</p>
          </div>
          <div class="flex flex-col gap-1.5">
            <UiInput
              v-model="form.email"
              placeholder="邮箱"
              autocomplete="email"
              @enter="handleRegister"
            >
              <template #prefix><Mail class="size-4" /></template>
            </UiInput>
            <p v-if="errors.email" class="text-xs text-danger">{{ errors.email }}</p>
          </div>
          <div class="flex flex-col gap-1.5">
            <UiInput
              v-model="form.password"
              type="password"
              placeholder="密码"
              autocomplete="new-password"
              @enter="handleRegister"
            >
              <template #prefix><Lock class="size-4" /></template>
            </UiInput>
            <p v-if="errors.password" class="text-xs text-danger">{{ errors.password }}</p>
          </div>
          <UiButton native-type="submit" :loading="loading" block size="lg" class="mt-2 tracking-wide">
            注册
          </UiButton>
        </form>

        <p class="m-0 text-center text-sm text-fg-secondary">
          已有账号？<router-link to="/login" class="ml-1 font-semibold text-brand hover:underline">返回登录</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Mail, Lock } from 'lucide-vue-next'
import UiInput from '@/components/ui/Input.vue'
import UiButton from '@/components/ui/Button.vue'
import { toast } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({ username: '', email: '', password: '' })
const errors = reactive<{ username: string; email: string; password: string }>({
  username: '',
  email: '',
  password: '',
})

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate(): boolean {
  const name = form.username.trim()
  if (!name) errors.username = '请输入用户名'
  else if (name.length < 3 || name.length > 80) errors.username = '用户名长度 3 至 80 字符'
  else errors.username = ''

  if (!form.email.trim()) errors.email = '请输入邮箱'
  else if (!EMAIL_RE.test(form.email.trim())) errors.email = '邮箱格式不正确'
  else errors.email = ''

  if (!form.password) errors.password = '请输入密码'
  else if (form.password.length < 6) errors.password = '密码至少 6 位'
  else errors.password = ''

  return !errors.username && !errors.email && !errors.password
}

async function handleRegister() {
  if (!validate()) return

  loading.value = true
  try {
    await authStore.register(form.username, form.email, form.password)
    toast.success('注册成功，请登录')
    router.push('/login')
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

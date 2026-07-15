<template>
  <div class="flex min-h-screen bg-canvas">
    <!-- 品牌区 — 暗色 marketing tier -->
    <aside class="relative hidden flex-[1.1] items-center overflow-hidden bg-[#0a0a14] px-16 py-20 text-fg-inverse lg:flex">
      <div
        class="pointer-events-none absolute inset-0 z-0"
        style="background: radial-gradient(circle at 25% 20%, rgba(143,114,208,0.25) 0%, transparent 55%)"
      />
      <div class="relative z-10 flex max-w-[520px] flex-col gap-8">
        <span class="text-2xs font-bold uppercase tracking-[0.22em] text-white/55">FANGCUN AI</span>
        <h1 class="m-0 text-5xl font-black leading-[1.05] tracking-tight text-[#f5f0ff]">
          为每一次推理，<br />
          构建可验证的<em class="font-normal italic text-[#c9b37e]">边界</em>。
        </h1>
        <p class="m-0 max-w-[44ch] text-lg leading-relaxed text-white/70">
          面向大模型的安全与能力评测平台。标准化 Benchmark、自动化红队，一处提交、全程可追溯。
        </p>
        <dl class="mt-4 grid grid-cols-2 gap-8 border-t border-white/10 pt-6">
          <div>
            <dt class="mb-2 text-2xs font-bold uppercase tracking-[0.18em] text-white/55">评测引擎</dt>
            <dd class="m-0 font-mono text-sm text-[#f5f0ff]">inspect_evals</dd>
          </div>
          <div>
            <dt class="mb-2 text-2xs font-bold uppercase tracking-[0.18em] text-white/55">覆盖能力</dt>
            <dd class="m-0 font-mono text-sm text-[#f5f0ff]">能力 · 安全 · 对齐</dd>
          </div>
        </dl>
        <span class="mt-3 h-px w-12 bg-[#c9b37e]" />
      </div>
    </aside>

    <!-- 表单区 — 亮色产品 UI -->
    <main class="flex flex-1 items-center justify-center bg-surface px-8 py-16">
      <div class="flex w-full max-w-[380px] flex-col gap-8">
        <header class="flex flex-col gap-2">
          <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">登录</span>
          <h2 class="m-0 text-3xl font-bold tracking-tight text-fg">欢迎回来</h2>
          <p class="m-0 text-sm text-fg-secondary">输入账号密码进入工作台。</p>
        </header>

        <form class="flex flex-col gap-4" @submit.prevent="handleLogin">
          <div class="flex flex-col gap-1.5">
            <UiInput
              v-model="form.username"
              placeholder="用户名"
              autocomplete="username"
              @enter="handleLogin"
            >
              <template #prefix><User class="size-4" /></template>
            </UiInput>
            <p v-if="errors.username" class="text-xs text-danger">{{ errors.username }}</p>
          </div>
          <div class="flex flex-col gap-1.5">
            <UiInput
              v-model="form.password"
              type="password"
              placeholder="密码"
              autocomplete="current-password"
              @enter="handleLogin"
            >
              <template #prefix><Lock class="size-4" /></template>
            </UiInput>
            <p v-if="errors.password" class="text-xs text-danger">{{ errors.password }}</p>
          </div>
          <UiButton native-type="submit" :loading="loading" block size="lg" class="mt-2 tracking-wide">
            登录
          </UiButton>
        </form>

        <p class="m-0 text-center text-sm text-fg-secondary">
          还没有账号？<router-link to="/register" class="ml-1 font-semibold text-brand hover:underline">注册账号</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import UiInput from '@/components/ui/Input.vue'
import UiButton from '@/components/ui/Button.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const errors = reactive<{ username: string; password: string }>({ username: '', password: '' })

function validate(): boolean {
  errors.username = form.username.trim() ? '' : '请输入用户名'
  errors.password = form.password ? '' : '请输入密码'
  return !errors.username && !errors.password
}

async function handleLogin() {
  if (!validate()) return
  loading.value = true
  try {
    await authStore.login({ username: form.username, password: form.password })
    toast.success('登录成功')
    router.push('/')
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

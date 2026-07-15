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
          {{ t('auth.loginBrandTitleLine1') }}<br />
          {{ t('auth.loginBrandTitleLine2') }}<em class="font-normal italic text-[#c9b37e]">{{ t('auth.loginBrandTitleEm') }}</em>{{ t('auth.loginBrandTitleEnd') }}
        </h1>
        <p class="m-0 max-w-[44ch] text-lg leading-relaxed text-white/70">
          {{ t('auth.loginBrandDesc') }}
        </p>
        <dl class="mt-4 grid grid-cols-2 gap-8 border-t border-white/10 pt-6">
          <div>
            <dt class="mb-2 text-2xs font-bold uppercase tracking-[0.18em] text-white/55">{{ t('auth.loginBrandStat1Label') }}</dt>
            <dd class="m-0 font-mono text-sm text-[#f5f0ff]">inspect_evals</dd>
          </div>
          <div>
            <dt class="mb-2 text-2xs font-bold uppercase tracking-[0.18em] text-white/55">{{ t('auth.loginBrandStat2Label') }}</dt>
            <dd class="m-0 font-mono text-sm text-[#f5f0ff]">{{ t('auth.loginBrandStat2Value') }}</dd>
          </div>
        </dl>
        <span class="mt-3 h-px w-12 bg-[#c9b37e]" />
      </div>
    </aside>

    <!-- 表单区 — 亮色产品 UI -->
    <main class="flex flex-1 items-center justify-center bg-surface px-8 py-16">
      <div class="flex w-full max-w-[380px] flex-col gap-8">
        <header class="flex flex-col gap-2">
          <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('auth.loginKicker') }}</span>
          <h2 class="m-0 text-3xl font-bold tracking-tight text-fg">{{ t('auth.loginTitle') }}</h2>
          <p class="m-0 text-sm text-fg-secondary">{{ t('auth.loginSubtitle') }}</p>
        </header>

        <form class="flex flex-col gap-4" @submit.prevent="handleLogin">
          <div class="flex flex-col gap-1.5">
            <UiInput
              v-model="form.username"
              :placeholder="t('auth.usernamePlaceholder')"
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
              :placeholder="t('auth.passwordPlaceholder')"
              autocomplete="current-password"
              @enter="handleLogin"
            >
              <template #prefix><Lock class="size-4" /></template>
            </UiInput>
            <p v-if="errors.password" class="text-xs text-danger">{{ errors.password }}</p>
          </div>
          <UiButton native-type="submit" :loading="loading" block size="lg" class="mt-2 tracking-wide">
            {{ t('auth.loginButton') }}
          </UiButton>
        </form>

        <p class="m-0 text-center text-sm text-fg-secondary">
          {{ t('auth.noAccount') }}<router-link to="/register" class="ml-1 font-semibold text-brand hover:underline">{{ t('auth.registerLink') }}</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { User, Lock } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import UiInput from '@/components/ui/Input.vue'
import UiButton from '@/components/ui/Button.vue'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const errors = reactive<{ username: string; password: string }>({ username: '', password: '' })

function validate(): boolean {
  errors.username = form.username.trim() ? '' : t('auth.usernameRequired')
  errors.password = form.password ? '' : t('auth.passwordRequired')
  return !errors.username && !errors.password
}

async function handleLogin() {
  if (!validate()) return
  loading.value = true
  try {
    await authStore.login({ username: form.username, password: form.password })
    toast.success(t('auth.loginSuccess'))
    router.push('/')
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('auth.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="grid min-h-screen bg-surface lg:grid-cols-[minmax(360px,0.9fr)_1.1fr]">
    <aside class="hidden items-center justify-center bg-[#111116] p-14 lg:flex">
      <div class="flex max-w-[420px] flex-col items-start gap-7">
        <img src="../assets/hero.png" alt="" class="h-auto w-44" />
        <div>
          <p class="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-white/55">FANGCUN IAM</p>
          <h1 class="m-0 text-4xl font-bold tracking-normal text-white">{{ t('auth.registerTitle') }}</h1>
        </div>
        <p class="m-0 max-w-[36ch] text-base leading-7 text-white/65">{{ t('auth.registerBrandDesc') }}</p>
      </div>
    </aside>

    <main class="flex items-center justify-center px-6 py-14 sm:px-12">
      <div class="flex w-full max-w-[420px] flex-col gap-8">
        <header class="flex flex-col gap-3">
          <span class="text-xs font-bold uppercase tracking-[0.16em] text-fg-tertiary">{{ t('auth.registerKicker') }}</span>
          <h2 class="m-0 text-3xl font-bold tracking-normal text-fg">{{ t('auth.registerTitle') }}</h2>
          <p class="m-0 text-sm leading-6 text-fg-secondary">{{ t('auth.registerSubtitle') }}</p>
        </header>

        <UiButton size="lg" block @click="authStore.register">
          <template #icon><UserPlus class="size-5" /></template>
          {{ t('auth.registerButton') }}
        </UiButton>

        <p class="m-0 text-center text-sm text-fg-secondary">
          {{ t('auth.haveAccount') }}
          <router-link to="/login" class="ml-1 font-semibold text-brand hover:underline">{{ t('auth.loginLink') }}</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { UserPlus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import UiButton from '@/components/ui/Button.vue'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const authStore = useAuthStore()
</script>

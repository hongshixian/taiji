<template>
  <div class="mx-auto flex max-w-[800px] flex-col gap-9">
    <header class="flex flex-col gap-2">
      <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.kicker') }}</span>
      <h1 class="m-0 text-3xl font-bold tracking-tight text-fg">{{ t('settings.title') }}</h1>
      <p class="m-0 text-sm text-fg-secondary">{{ t('settings.subtitle') }}</p>
    </header>

    <!-- 外观 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-1.5">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.appearanceKicker') }}</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">{{ t('settings.themeTitle') }}</h2>
      </header>
      <div class="flex items-center justify-between gap-7">
        <div class="flex flex-col gap-0.5">
          <div class="text-sm font-semibold text-fg">{{ t('settings.themeMode') }}</div>
          <div class="text-sm text-fg-secondary">{{ t('settings.themeModeDesc') }}</div>
        </div>
        <UiSwitch :model-value="isDark" @update:model-value="toggleTheme" />
      </div>
    </section>

    <!-- 安全 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-1.5">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.securityKicker') }}</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">{{ t('settings.passwordTitle') }}</h2>
      </header>
      <div class="flex items-center justify-between gap-7">
        <div class="flex flex-col gap-0.5">
          <div class="text-sm font-semibold text-fg">{{ t('settings.manageAccount') }}</div>
          <div class="text-sm text-fg-secondary">{{ t('settings.changePasswordDesc') }}</div>
        </div>
        <UiButton variant="secondary" :loading="accountLoading" @click="openAccountManagement">
          {{ t('settings.manageAccount') }}
        </UiButton>
      </div>
    </section>

    <!-- 关于 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-1.5">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.aboutKicker') }}</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">{{ t('settings.aboutTitle') }}</h2>
      </header>
      <dl class="m-0 grid grid-cols-1 gap-x-9 gap-y-6 sm:grid-cols-2">
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.projectLabel') }}</dt>
          <dd class="m-0 font-mono text-sm font-medium text-fg">{{ t('settings.projectValue') }}</dd>
        </div>
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.versionLabel') }}</dt>
          <dd class="m-0 font-mono text-sm font-medium text-fg">v0.1.0</dd>
        </div>
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.stackLabel') }}</dt>
          <dd class="m-0 text-sm font-medium text-fg">Flask 3 · Vue 3 · Celery · Redis</dd>
        </div>
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('settings.licenseLabel') }}</dt>
          <dd class="m-0 text-sm font-medium text-fg">MIT License</dd>
        </div>
      </dl>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import UiSwitch from '@/components/ui/Switch.vue'
import UiButton from '@/components/ui/Button.vue'
import { toast } from '@/lib/toast'
import { getAccountManagementUrl } from '@/api/auth'
import { applyTheme, isDarkActive } from '@/utils/theme'

const { t } = useI18n()

const isDark = ref(isDarkActive())

function toggleTheme(value: boolean) {
  isDark.value = value
  applyTheme(value)
}

const accountLoading = ref(false)

async function openAccountManagement() {
  accountLoading.value = true
  try {
    const { data } = await getAccountManagementUrl()
    window.location.assign(data.data.account_url)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('settings.accountOpenFailed'))
  } finally {
    accountLoading.value = false
  }
}
</script>

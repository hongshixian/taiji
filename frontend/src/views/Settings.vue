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
          <div class="text-sm font-semibold text-fg">{{ t('settings.changePassword') }}</div>
          <div class="text-sm text-fg-secondary">{{ t('settings.changePasswordDesc') }}</div>
        </div>
        <UiButton variant="secondary" @click="pwdDialogVisible = true">{{ t('settings.changePassword') }}</UiButton>
      </div>
    </section>

    <!-- 修改密码弹窗 -->
    <UiDialog v-model="pwdDialogVisible" :title="t('settings.changePassword')" width="460px">
      <form class="flex flex-col gap-4" @submit.prevent="handleChangePassword">
        <UiFormItem :label="t('settings.oldPasswordLabel')" required :error="errors.oldPassword">
          <UiInput
            v-model="pwdForm.oldPassword"
            type="password"
            :placeholder="t('settings.oldPasswordPlaceholder')"
            autocomplete="current-password"
          />
        </UiFormItem>
        <UiFormItem :label="t('settings.newPasswordLabel')" required :error="errors.newPassword">
          <UiInput
            v-model="pwdForm.newPassword"
            type="password"
            :placeholder="t('settings.newPasswordPlaceholder')"
            autocomplete="new-password"
          />
        </UiFormItem>
        <UiFormItem :label="t('settings.confirmPasswordLabel')" required :error="errors.confirmPassword">
          <UiInput
            v-model="pwdForm.confirmPassword"
            type="password"
            :placeholder="t('settings.confirmPasswordPlaceholder')"
            autocomplete="new-password"
            @enter="handleChangePassword"
          />
        </UiFormItem>
      </form>
      <template #footer>
        <UiButton variant="secondary" @click="closePwdDialog">{{ t('common.cancel') }}</UiButton>
        <UiButton :loading="pwdSubmitting" @click="handleChangePassword">{{ t('settings.confirmChange') }}</UiButton>
      </template>
    </UiDialog>

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
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import UiSwitch from '@/components/ui/Switch.vue'
import UiButton from '@/components/ui/Button.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiInput from '@/components/ui/Input.vue'
import { toast } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import { applyTheme, isDarkActive } from '@/utils/theme'

const { t } = useI18n()
const authStore = useAuthStore()

const isDark = ref(isDarkActive())

function toggleTheme(value: boolean) {
  isDark.value = value
  applyTheme(value)
}

const pwdDialogVisible = ref(false)
const pwdSubmitting = ref(false)
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const errors = reactive<{ oldPassword: string; newPassword: string; confirmPassword: string }>({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

function validate(): boolean {
  errors.oldPassword = pwdForm.oldPassword ? '' : t('settings.oldPasswordRequired')

  if (!pwdForm.newPassword) errors.newPassword = t('settings.newPasswordRequired')
  else if (pwdForm.newPassword.length < 6) errors.newPassword = t('settings.newPasswordMin')
  else errors.newPassword = ''

  if (!pwdForm.confirmPassword) errors.confirmPassword = t('settings.confirmPasswordRequired')
  else if (pwdForm.confirmPassword !== pwdForm.newPassword) errors.confirmPassword = t('settings.passwordMismatch')
  else errors.confirmPassword = ''

  return !errors.oldPassword && !errors.newPassword && !errors.confirmPassword
}

function resetPwdForm() {
  pwdForm.oldPassword = ''
  pwdForm.newPassword = ''
  pwdForm.confirmPassword = ''
  errors.oldPassword = ''
  errors.newPassword = ''
  errors.confirmPassword = ''
}

function closePwdDialog() {
  pwdDialogVisible.value = false
  resetPwdForm()
}

async function handleChangePassword() {
  if (!validate()) return

  pwdSubmitting.value = true
  try {
    await changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    pwdDialogVisible.value = false
    toast.success(t('settings.changeSuccess'))
    setTimeout(() => {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('originalTenantId')
      authStore.user = null
      authStore.isLoggedIn = false
      window.location.hash = '#/login'
    }, 1500)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('settings.changeFailed'))
  } finally {
    pwdSubmitting.value = false
  }
}
</script>

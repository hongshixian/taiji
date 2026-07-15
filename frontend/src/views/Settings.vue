<template>
  <div class="mx-auto flex max-w-[800px] flex-col gap-9">
    <header class="flex flex-col gap-2">
      <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">个人 · 偏好</span>
      <h1 class="m-0 text-3xl font-bold tracking-tight text-fg">通用设置</h1>
      <p class="m-0 text-sm text-fg-secondary">外观、安全、关于。修改密码后会自动退出登录。</p>
    </header>

    <!-- 外观 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-1.5">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">外观</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">主题</h2>
      </header>
      <div class="flex items-center justify-between gap-7">
        <div class="flex flex-col gap-0.5">
          <div class="text-sm font-semibold text-fg">主题模式</div>
          <div class="text-sm text-fg-secondary">切换浅色 / 深色界面。系统设置会被本地偏好覆盖。</div>
        </div>
        <UiSwitch :model-value="isDark" @update:model-value="toggleTheme" />
      </div>
    </section>

    <!-- 安全 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-1.5">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">安全</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">登录密码</h2>
      </header>
      <div class="flex items-center justify-between gap-7">
        <div class="flex flex-col gap-0.5">
          <div class="text-sm font-semibold text-fg">修改密码</div>
          <div class="text-sm text-fg-secondary">修改后所有现有 token 立即失效，需要重新登录。</div>
        </div>
        <UiButton variant="secondary" @click="pwdDialogVisible = true">修改密码</UiButton>
      </div>
    </section>

    <!-- 修改密码弹窗 -->
    <UiDialog v-model="pwdDialogVisible" title="修改密码" width="460px">
      <form class="flex flex-col gap-4" @submit.prevent="handleChangePassword">
        <UiFormItem label="当前密码" required :error="errors.oldPassword">
          <UiInput
            v-model="pwdForm.oldPassword"
            type="password"
            placeholder="请输入当前密码"
            autocomplete="current-password"
          />
        </UiFormItem>
        <UiFormItem label="新密码" required :error="errors.newPassword">
          <UiInput
            v-model="pwdForm.newPassword"
            type="password"
            placeholder="至少 6 位"
            autocomplete="new-password"
          />
        </UiFormItem>
        <UiFormItem label="确认新密码" required :error="errors.confirmPassword">
          <UiInput
            v-model="pwdForm.confirmPassword"
            type="password"
            placeholder="再次输入新密码"
            autocomplete="new-password"
            @enter="handleChangePassword"
          />
        </UiFormItem>
      </form>
      <template #footer>
        <UiButton variant="secondary" @click="closePwdDialog">取消</UiButton>
        <UiButton :loading="pwdSubmitting" @click="handleChangePassword">确认修改</UiButton>
      </template>
    </UiDialog>

    <!-- 关于 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-1.5">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">关于</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">项目信息</h2>
      </header>
      <dl class="m-0 grid grid-cols-1 gap-x-9 gap-y-6 sm:grid-cols-2">
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">项目</dt>
          <dd class="m-0 font-mono text-sm font-medium text-fg">方寸 AI 测评平台</dd>
        </div>
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">版本</dt>
          <dd class="m-0 font-mono text-sm font-medium text-fg">v0.1.0</dd>
        </div>
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">技术栈</dt>
          <dd class="m-0 text-sm font-medium text-fg">Flask 3 · Vue 3 · Celery · Redis</dd>
        </div>
        <div class="flex flex-col gap-2">
          <dt class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">协议</dt>
          <dd class="m-0 text-sm font-medium text-fg">MIT License</dd>
        </div>
      </dl>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import UiSwitch from '@/components/ui/Switch.vue'
import UiButton from '@/components/ui/Button.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiInput from '@/components/ui/Input.vue'
import { toast } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import { applyTheme, isDarkActive } from '@/utils/theme'

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
  errors.oldPassword = pwdForm.oldPassword ? '' : '请输入当前密码'

  if (!pwdForm.newPassword) errors.newPassword = '请输入新密码'
  else if (pwdForm.newPassword.length < 6) errors.newPassword = '新密码至少 6 位'
  else errors.newPassword = ''

  if (!pwdForm.confirmPassword) errors.confirmPassword = '请再次输入新密码'
  else if (pwdForm.confirmPassword !== pwdForm.newPassword) errors.confirmPassword = '两次输入的密码不一致'
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
    toast.success('密码已修改，即将退出登录')
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
    toast.error(e.response?.data?.message || '修改失败')
  } finally {
    pwdSubmitting.value = false
  }
}
</script>

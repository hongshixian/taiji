/**
 * RBAC 权限判断 composable
 *
 * 用法：
 *   const { has, hasAny, hasAll } = usePermission()
 *   if (has('user:write')) { ... }
 *   v-if="has('role:write')"
 */

import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const perms = computed(() => new Set(authStore.user?.permissions ?? []))

  /** 是否拥有指定权限 */
  function has(code) {
    return perms.value.has(code)
  }

  /** 是否拥有任意一个权限（OR） */
  function hasAny(...codes) {
    return codes.some((c) => perms.value.has(c))
  }

  /** 是否拥有全部指定权限（AND） */
  function hasAll(...codes) {
    return codes.every((c) => perms.value.has(c))
  }

  return { has, hasAny, hasAll, perms }
}

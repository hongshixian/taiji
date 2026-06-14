/**
 * 主题切换 helper:同步 html.dark (用于 Element Plus 暗色变量) 与
 * data-theme (用于 Fangcun semantic.css 的 [data-theme="dark"] 选择器)。
 */

const STORAGE_KEY = 'fangcun-theme'

export function applyTheme(isDark) {
  const root = document.documentElement
  root.classList.toggle('dark', isDark)
  root.setAttribute('data-theme', isDark ? 'dark' : 'light')
  localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light')
}

export function isDarkActive() {
  return document.documentElement.classList.contains('dark')
}

export function getStoredTheme() {
  return localStorage.getItem(STORAGE_KEY)
}

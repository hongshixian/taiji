import { createI18n } from 'vue-i18n'
import zh from './locales/zh'
import en from './locales/en'

export type AppLocale = 'zh' | 'en'
const STORAGE_KEY = 'app_locale'

export function getStoredLocale(): AppLocale {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'zh' || saved === 'en') return saved
  // 默认跟随浏览器，非中文一律英文
  return navigator.language?.toLowerCase().startsWith('zh') ? 'zh' : 'zh'
}

export function setStoredLocale(locale: AppLocale) {
  localStorage.setItem(STORAGE_KEY, locale)
}

export const i18n = createI18n({
  legacy: false,
  locale: getStoredLocale(),
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export function setLocale(locale: AppLocale) {
  i18n.global.locale.value = locale
  setStoredLocale(locale)
  document.documentElement.setAttribute('lang', locale === 'zh' ? 'zh-CN' : 'en')
}

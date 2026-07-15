import { createApp } from 'vue'
import './assets/theme.css'
import './assets/tailwind.css'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { applyTheme, getStoredTheme } from './utils/theme'
import { i18n, getStoredLocale } from './i18n'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)

// 初始化主题：data-theme 驱动 semantic tokens（Tailwind 工具类随之翻转）
const savedTheme = getStoredTheme()
const prefersDark = !savedTheme && window.matchMedia?.('(prefers-color-scheme: dark)').matches
applyTheme(savedTheme === 'dark' || prefersDark)

// 初始化语言
document.documentElement.setAttribute('lang', getStoredLocale() === 'zh' ? 'zh-CN' : 'en')

app.mount('#app')

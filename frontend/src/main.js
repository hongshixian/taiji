import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './assets/theme.css'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

const app = createApp(App)

// 注册所有 Element Plus 图标为全局组件
for (const [name, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, comp)
}

app.use(ElementPlus)
app.use(createPinia())
app.use(router)

// 初始化暗色模式
const savedTheme = localStorage.getItem('taiji-theme')
if (savedTheme === 'dark' ||
    (!savedTheme && window.matchMedia?.('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark')
}

app.mount('#app')

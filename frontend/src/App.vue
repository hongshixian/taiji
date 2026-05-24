<template>
  <div id="app">
    <el-container v-if="isLoggedIn" class="app-layout">
      <!-- 顶栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <span class="collapse-btn" @click="collapsed = !collapsed">☰</span>
          <span class="logo">☯ 太极</span>
        </div>
        <div class="header-right">
          <span class="username">{{ authStore.user?.username }}</span>
          <el-button text @click="authStore.logout()">退出</el-button>
        </div>
      </el-header>
      <el-container>
        <!-- 侧边栏 -->
        <el-aside :width="collapsed ? '64px' : '200px'" class="app-aside">
          <el-menu
            :default-active="currentRoute"
            :collapse="collapsed"
            router
            class="side-menu"
          >
            <el-menu-item index="/">
              <span class="menu-icon">🏠</span>
              <template #title>主页</template>
            </el-menu-item>
            <el-menu-item index="/tasks">
              <span class="menu-icon">📋</span>
              <template #title>任务管理</template>
            </el-menu-item>
            <el-menu-item index="/users">
              <span class="menu-icon">👥</span>
              <template #title>用户管理</template>
            </el-menu-item>
            <el-menu-item index="/settings">
              <span class="menu-icon">⚙️</span>
              <template #title>通用设置</template>
            </el-menu-item>
          </el-menu>
        </el-aside>
        <!-- 主内容区 -->
        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    <router-view v-else />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const authStore = useAuthStore()
const collapsed = ref(false)

const isLoggedIn = computed(() => authStore.isLoggedIn)
const currentRoute = computed(() => route.path)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.app-layout {
  height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 56px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.collapse-btn {
  font-size: 18px;
  cursor: pointer;
  color: #606266;
  user-select: none;
}
.collapse-btn:hover {
  color: #409eff;
}
.logo {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: #606266;
  font-size: 14px;
}
.app-aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  transition: width 0.3s;
  overflow: hidden;
}
.side-menu {
  border-right: none !important;
  height: 100%;
}
.side-menu .menu-icon { font-size: 16px; }
.app-main {
  background: #f5f7fa;
  min-height: calc(100vh - 56px);
  padding: 24px;
}
</style>

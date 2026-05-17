<template>
  <div id="app">
    <el-container v-if="isLoggedIn" class="app-layout">
      <el-header class="app-header">
        <span class="logo">☯ 太极</span>
        <el-menu
          mode="horizontal"
          :default-active="currentRoute"
          router
          class="header-menu"
        >
          <el-menu-item index="/">网页分析</el-menu-item>
          <el-menu-item index="/history">历史任务</el-menu-item>
        </el-menu>
        <div class="header-right">
          <span class="username">{{ authStore.user?.username }}</span>
          <el-button text @click="authStore.logout()">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
    <router-view v-else />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const authStore = useAuthStore()

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
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}
.logo {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  margin-right: 40px;
}
.header-menu {
  flex: 1;
  border-bottom: none !important;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.username {
  color: #606266;
  font-size: 14px;
}
</style>
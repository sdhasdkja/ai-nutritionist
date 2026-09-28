<template>
  <el-container class="min-h-screen">
    <!-- 侧边栏 -->
    <el-aside width="240px" class="bg-gradient-to-b from-emerald-700 to-emerald-900 text-white">
      <div class="p-6 text-center border-b border-emerald-600">
        <h1 class="text-xl font-bold">🥗 AI营养师</h1>
        <p class="text-emerald-200 text-sm mt-1">智能饮食管理</p>
      </div>

      <el-menu :default-active="activeMenu" router class="border-0 menu-transparent">
        <el-menu-item index="/" class="text-white hover:bg-emerald-600">
          <el-icon><HomeFilled /></el-icon>
          <span>控制台</span>
        </el-menu-item>

        <el-menu-item index="/health-reports" class="text-white hover:bg-emerald-600">
          <el-icon><Document /></el-icon>
          <span>健康报告</span>
        </el-menu-item>

        <el-menu-item index="/recipes" class="text-white hover:bg-emerald-600">
          <el-icon><Food /></el-icon>
          <span>我的食谱</span>
        </el-menu-item>

        <el-menu-item index="/preferences" class="text-white hover:bg-emerald-600">
          <el-icon><Setting /></el-icon>
          <span>口味偏好</span>
        </el-menu-item>

        <el-menu-item index="/chat" class="text-white hover:bg-emerald-600">
          <el-icon><ChatDotRound /></el-icon>
          <span>营养师问答</span>
        </el-menu-item>

        <el-menu-item index="/profile" class="text-white hover:bg-emerald-600">
          <el-icon><User /></el-icon>
          <span>个人资料</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="bg-white border-b flex items-center justify-between px-6">
        <div></div>
        <div class="flex items-center gap-4">
          <span class="text-gray-600">{{ userStore.userInfo?.username }}</span>
          <el-button text @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>

      <el-main class="bg-gray-50 p-6">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { HomeFilled, Document, Food, Setting, User, ChatDotRound } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

onMounted(() => {
  if (!userStore.userInfo) {
    userStore.fetchUserInfo().catch(() => {})
  }
})
</script>

<style scoped>
.menu-transparent {
  background-color: transparent;
}
.menu-transparent :deep(.el-menu-item.is-active) {
  background-color: rgba(16, 185, 129, 0.3);
}
</style>

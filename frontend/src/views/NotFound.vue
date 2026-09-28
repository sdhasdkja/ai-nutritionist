<template>
  <div class="min-h-screen flex flex-col items-center justify-center bg-gray-50">
    <h1 class="text-6xl font-bold text-emerald-600 mb-4">404</h1>
    <p class="text-gray-500 mb-6">页面不存在或已被删除</p>
    <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<script setup>
</script>

<template>
  <div v-loading="loading">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">{{ recipe?.name || '食谱详情' }}</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <template v-if="recipe">
      <!-- 概要信息 -->
      <el-card class="mb-6">
        <div class="flex flex-wrap gap-8 items-center">
          <div>
            <div class="text-gray-500 text-sm mb-1">总热量</div>
            <div class="text-2xl font-bold text-orange-500">🔥 {{ recipe.total_calories }} kcal</div>
          </div>
          <div v-for="(label, key) in nutritionLabels" :key="key">
            <div class="text-gray-500 text-sm mb-1">{{ label }}</div>
            <div class="text-2xl font-bold text-emerald-600">{{ recipe.nutrition_info?.[key] ?? '-' }} g</div>
          </div>
          <div>
            <div class="text-gray-500 text-sm mb-1">生成时间</div>
            <div class="text-gray-700">{{ formatDate(recipe.created_at) }}</div>
          </div>
          <div v-if="recipe.nutrition_info?.iterations">
            <div class="text-gray-500 text-sm mb-1">审核轮次</div>
            <el-tag type="success">质量审核 {{ recipe.nutrition_info.iterations }} 轮通过</el-tag>
          </div>
        </div>
      </el-card>

      <!-- 食谱内容 -->
      <el-card>
        <template #header>
          <span class="font-bold">🍽️ 食谱内容</span>
        </template>
        <div class="recipe-content text-gray-700 leading-relaxed" v-html="renderedContent"></div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const loading = ref(false)
const recipe = ref(null)

const nutritionLabels = { protein: '蛋白质', carbs: '碳水', fat: '脂肪' }

// 轻量markdown渲染（标题/加粗/列表）
const renderedContent = computed(() => {
  const raw = recipe.value?.description || ''
  if (!raw) return ''
  const escaped = raw
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return escaped
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\s*[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, '<ul>$1</ul>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
})

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchRecipe = async () => {
  loading.value = true
  try {
    recipe.value = await api.recipes.get(route.params.id)
  } catch (error) {
    console.error('获取食谱失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecipe)
</script>

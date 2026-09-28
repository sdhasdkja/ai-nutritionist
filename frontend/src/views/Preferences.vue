<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 mb-6">口味偏好</h2>

    <!-- 添加偏好 -->
    <el-card class="mb-6">
      <template #header>
        <span class="font-bold">➕ 添加偏好（生成食谱时AI会参考）</span>
      </template>

      <el-form :inline="true" :model="addForm">
        <el-form-item label="类型">
          <el-select v-model="addForm.preference_type" style="width: 140px">
            <el-option label="喜欢的食物" value="favorite_food" />
            <el-option label="不喜欢的食物" value="disliked_food" />
            <el-option label="偏好菜系" value="cuisine" />
            <el-option label="过敏食物" value="allergy" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="addForm.preference_value"
            placeholder="如：川菜 / 香菜 / 海鲜过敏"
            style="width: 240px"
            @keyup.enter="handleAdd"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="adding" @click="handleAdd">添加</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 偏好列表（按类型分组） -->
    <el-card v-loading="loading">
      <template #header>
        <span class="font-bold">📋 我的偏好</span>
      </template>

      <div v-for="(label, type) in typeLabels" :key="type" class="mb-4">
        <div class="text-gray-500 text-sm mb-2">{{ label }}</div>
        <div class="flex flex-wrap gap-2">
          <el-tag
            v-for="p in preferencesByType(type)"
            :key="p.id"
            :type="tagColor(type)"
            closable
            @close="handleDelete(p)"
          >
            {{ p.preference_value }}
          </el-tag>
          <span v-if="preferencesByType(type).length === 0" class="text-gray-300 text-sm">暂无</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const adding = ref(false)
const preferences = ref([])

const addForm = reactive({
  preference_type: 'favorite_food',
  preference_value: ''
})

const typeLabels = {
  favorite_food: '喜欢的食物',
  disliked_food: '不喜欢的食物',
  cuisine: '偏好菜系',
  allergy: '过敏食物（生成食谱时会严格规避）'
}

const tagColor = (type) => {
  const map = { favorite_food: 'success', disliked_food: 'warning', cuisine: '', allergy: 'danger' }
  return map[type] || 'info'
}

const preferencesByType = (type) => {
  return preferences.value.filter(p => p.preference_type === type)
}

const fetchPreferences = async () => {
  loading.value = true
  try {
    preferences.value = await api.preferences.list()
  } catch (error) {
    console.error('获取偏好失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = async () => {
  if (!addForm.preference_value.trim()) {
    ElMessage.warning('请输入偏好内容')
    return
  }
  adding.value = true
  try {
    await api.preferences.create({ ...addForm, preference_value: addForm.preference_value.trim() })
    ElMessage.success('添加成功')
    addForm.preference_value = ''
    await fetchPreferences()
  } catch (error) {
    console.error('添加失败:', error)
  } finally {
    adding.value = false
  }
}

const handleDelete = async (p) => {
  try {
    await api.preferences.remove(p.id)
    await fetchPreferences()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

onMounted(fetchPreferences)
</script>

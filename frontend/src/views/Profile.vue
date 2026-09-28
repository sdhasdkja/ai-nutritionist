<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 mb-6">个人资料</h2>

    <el-card style="max-width: 600px">
      <template #header>
        <span class="font-bold">👤 基本信息（身高体重年龄会影响AI营养规划）</span>
      </template>

      <el-form
        v-loading="loading"
        :model="form"
        label-width="100px"
        size="large"
      >
        <el-form-item label="用户名">
          <el-input v-model="form.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" placeholder="真实姓名（选填）" />
        </el-form-item>
        <el-form-item label="年龄">
          <el-input-number v-model="form.age" :min="1" :max="120" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="form.gender" placeholder="请选择" style="width: 160px">
            <el-option label="男" value="male" />
            <el-option label="女" value="female" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="身高 (cm)">
          <el-input-number v-model="form.height" :min="50" :max="250" :precision="1" />
        </el-form-item>
        <el-form-item label="体重 (kg)">
          <el-input-number v-model="form.weight" :min="20" :max="300" :precision="1" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)

const form = reactive({
  username: '',
  email: '',
  full_name: '',
  age: null,
  gender: null,
  height: null,
  weight: null
})

const fetchProfile = async () => {
  loading.value = true
  try {
    const user = await api.auth.me()
    Object.assign(form, {
      username: user.username,
      email: user.email,
      full_name: user.full_name || '',
      age: user.age,
      gender: user.gender,
      height: user.height,
      weight: user.weight
    })
  } catch (error) {
    console.error('获取资料失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await api.users.updateMe({
      full_name: form.full_name || null,
      age: form.age,
      gender: form.gender,
      height: form.height,
      weight: form.weight
    })
    ElMessage.success('保存成功')
    await userStore.fetchUserInfo()
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

onMounted(fetchProfile)
</script>

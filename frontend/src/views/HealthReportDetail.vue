<template>
  <div v-loading="loading">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">{{ report?.report_name || '报告详情' }}</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <template v-if="report">
      <!-- AI解析摘要 -->
      <el-card class="mb-6">
        <template #header>
          <span class="font-bold">📊 指标解析结果</span>
        </template>
        <el-alert
          :title="report.analysis_result?.summary || '暂无解析结果'"
          :type="alertType"
          :closable="false"
          show-icon
          class="mb-4"
        />

        <el-table :data="report.analysis_result?.indicators || []" stripe>
          <el-table-column prop="name" label="指标" width="120" />
          <el-table-column label="数值" width="140">
            <template #default="{ row }">
              {{ row.value }} {{ row.unit }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">
                {{ statusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="advice" label="饮食建议" />
        </el-table>
      </el-card>

      <!-- 报告原文 -->
      <el-card>
        <template #header>
          <span class="font-bold">📄 报告原文</span>
        </template>
        <pre class="whitespace-pre-wrap text-gray-700 text-sm leading-relaxed">{{ report.report_content }}</pre>
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
const report = ref(null)

const alertType = computed(() => {
  const count = report.value?.analysis_result?.abnormal_count ?? 0
  if (count === 0) return 'success'
  if (count <= 2) return 'warning'
  return 'error'
})

const statusType = (status) => {
  if (status === 'normal') return 'success'
  if (status === 'high') return 'danger'
  return 'warning'
}

const statusText = (status) => {
  if (status === 'normal') return '正常'
  if (status === 'high') return '偏高'
  return '偏低'
}

const fetchReport = async () => {
  loading.value = true
  try {
    report.value = await api.healthReports.get(route.params.id)
  } catch (error) {
    console.error('获取报告失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchReport)
</script>

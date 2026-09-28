<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">健康报告</h2>
      <div class="flex gap-3">
        <!-- 文件上传（PDF/TXT/图片自动解析） -->
        <el-upload
          :show-file-list="false"
          :auto-upload="true"
          :http-request="handleFileUpload"
          accept=".pdf,.txt,.md,.log,.csv,.jpg,.jpeg,.png,.bmp,.webp"
        >
          <el-button type="success" :loading="fileParsing">
            <el-icon class="mr-2"><Paperclip /></el-icon>
            上传文件解析
          </el-button>
        </el-upload>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon class="mr-2"><Upload /></el-icon>
          粘贴文本
        </el-button>
      </div>
    </div>

    <!-- 报告列表 -->
    <el-card v-loading="loading">
      <el-table :data="reports" stripe style="width: 100%">
        <el-table-column prop="report_name" label="报告名称" />

        <el-table-column label="血糖 (mmol/L)" width="120">
          <template #default="{ row }">
            <el-tag :type="getGlucoseType(row.blood_glucose)">
              {{ row.blood_glucose ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="血压 (mmHg)" width="140">
          <template #default="{ row }">
            {{ row.blood_pressure_systolic ?? '-' }}/{{ row.blood_pressure_diastolic ?? '-' }}
          </template>
        </el-table-column>

        <el-table-column label="尿酸 (μmol/L)" width="120">
          <template #default="{ row }">
            {{ row.uric_acid ?? '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/health-reports/${row.id}`)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传体检报告" width="600px">
      <el-alert
        type="info"
        :closable="false"
        class="mb-4"
        title="支持粘贴文本，或拖入PDF/图片文件；AI会自动提取指标并评估"
      />
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="报告名称">
          <el-input v-model="uploadForm.report_name" placeholder="请输入报告名称" />
        </el-form-item>
        <el-form-item label="报告内容">
          <el-input
            v-model="uploadForm.report_content"
            type="textarea"
            :rows="10"
            placeholder="请粘贴体检报告内容，例如：&#10;空腹血糖 6.8 mmol/L&#10;血压 135/88 mmHg&#10;尿酸 460 μmol/L&#10;总胆固醇 5.8 mmol/L&#10;甘油三酯 2.1 mmol/L"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传分析</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { Upload, Paperclip } from '@element-plus/icons-vue'

const loading = ref(false)
const uploading = ref(false)
const fileParsing = ref(false)
const reports = ref([])
const showUploadDialog = ref(false)

const uploadForm = reactive({
  report_name: '',
  report_content: ''
})

// 文件上传：后端解析后回填表单，用户确认再入库
const handleFileUpload = async (options) => {
  const file = options.file
  fileParsing.value = true
  try {
    const res = await api.healthReports.uploadFile(file)
    uploadForm.report_name = res.report_name
    uploadForm.report_content = res.report_content
    showUploadDialog.value = true
    ElMessage.success('文件解析成功，请确认内容后保存')
  } catch (error) {
    console.error('文件解析失败:', error)
  } finally {
    fileParsing.value = false
  }
}

const fetchReports = async () => {
  loading.value = true
  try {
    reports.value = await api.healthReports.list()
  } catch (error) {
    console.error('获取报告列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleUpload = async () => {
  if (!uploadForm.report_name || !uploadForm.report_content) {
    ElMessage.warning('请填写完整信息')
    return
  }

  uploading.value = true
  try {
    await api.healthReports.create(uploadForm)
    ElMessage.success('报告上传成功，已自动解析指标')
    showUploadDialog.value = false
    uploadForm.report_name = ''
    uploadForm.report_content = ''
    await fetchReports()
  } catch (error) {
    console.error('上传失败:', error)
  } finally {
    uploading.value = false
  }
}

const getGlucoseType = (value) => {
  if (!value) return 'info'
  if (value < 6.1) return 'success'
  if (value < 7.0) return 'warning'
  return 'danger'
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(fetchReports)
</script>

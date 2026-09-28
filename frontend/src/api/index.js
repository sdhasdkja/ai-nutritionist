import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api',
  // 多Agent工作流生成食谱约需1-3分钟，全局超时放宽到5分钟
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：直接返回 response.data
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 请求失败提示（生成食谱等长请求被手动取消时静默）
    if (error.code !== 'ERR_CANCELED') {
      const message = error.response?.data?.detail || error.message || '请求失败'
      ElMessage.error(String(message))
    }
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

const api = {
  auth: {
    // 后端为 OAuth2 表单格式
    login: (data) => apiClient.post('/auth/login', new URLSearchParams(data), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }),
    register: (data) => apiClient.post('/auth/register', data),
    me: () => apiClient.get('/users/me')
  },

  users: {
    updateMe: (data) => apiClient.put('/users/me', data)
  },

  healthReports: {
    list: () => apiClient.get('/health-reports'),
    get: (id) => apiClient.get(`/health-reports/${id}`),
    create: (data) => apiClient.post('/health-reports', data),
    remove: (id) => apiClient.delete(`/health-reports/${id}`),
    // 上传文件提取文本（PDF/TXT/图片），Content-Type 交由浏览器带 boundary 设置
    uploadFile: (file) => {
      const fd = new FormData()
      fd.append('file', file)
      return apiClient.post('/health-reports/upload', fd, {
        headers: { 'Content-Type': undefined },
        timeout: 120000,
      })
    }
  },

  chat: {
    send: (message, history) => apiClient.post('/chat', { message, history }),
  },

  recipes: {
    list: () => apiClient.get('/recipes'),
    get: (id) => apiClient.get(`/recipes/${id}`),
    generate: (data) => apiClient.post('/recipes/generate', data),
    remove: (id) => apiClient.delete(`/recipes/${id}`)
  },

  preferences: {
    list: () => apiClient.get('/preferences'),
    create: (data) => apiClient.post('/preferences', data),
    remove: (id) => apiClient.delete(`/preferences/${id}`)
  }
}

export default api

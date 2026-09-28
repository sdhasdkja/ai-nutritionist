<template>
  <div class="flex flex-col" style="height: calc(100vh - 120px)">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold text-gray-800">营养师问答</h2>
      <el-button text type="danger" @click="clearChat">清空对话</el-button>
    </div>

    <!-- 消息列表 -->
    <el-card class="flex-1 overflow-hidden" body-class="h-full">
      <div ref="listRef" class="h-full overflow-y-auto pr-2 space-y-4">
        <!-- 欢迎语 -->
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center">
          <div class="text-5xl mb-4">🥗</div>
          <div class="text-gray-600 mb-1">你好，我是AI营养师</div>
          <div class="text-gray-400 text-sm mb-6">基于营养学知识库回答你的健康饮食问题</div>
          <div class="flex flex-wrap gap-2 justify-center max-w-lg">
            <el-tag
              v-for="q in suggestions"
              :key="q"
              class="cursor-pointer"
              effect="plain"
              @click="input = q; handleSend()"
            >{{ q }}</el-tag>
          </div>
        </div>

        <!-- 对话气泡 -->
        <div v-for="(msg, i) in messages" :key="i" class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
          <div
            class="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
            :class="msg.role === 'user'
              ? 'bg-emerald-600 text-white rounded-br-sm'
              : 'bg-gray-100 text-gray-800 rounded-bl-sm'"
          >
            <template v-if="msg.loading">
              <span class="inline-flex gap-1 items-center">
                <span class="dot animate-bounce">●</span>
                <span class="dot animate-bounce" style="animation-delay:0.15s">●</span>
                <span class="dot animate-bounce" style="animation-delay:0.3s">●</span>
                <span class="ml-1 text-gray-400">营养师思考中</span>
              </span>
            </template>
            <template v-else>
              {{ msg.content }}
              <!-- 引用来源 -->
              <div v-if="msg.sources?.length" class="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-400">
                参考资料：
                <el-tag v-for="s in msg.sources" :key="s.category" size="small" type="info" effect="plain" class="mr-1">
                  {{ s.category }}
                </el-tag>
              </div>
            </template>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 输入区 -->
    <div class="mt-4 flex gap-3 items-end">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        placeholder="输入你的营养健康问题，Ctrl+Enter 发送"
        :disabled="sending"
        @keydown.ctrl.enter="handleSend"
      />
      <el-button type="primary" size="large" :loading="sending" @click="handleSend">
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'

const listRef = ref(null)
const input = ref('')
const sending = ref(false)
const messages = ref([])

const suggestions = [
  '血糖偏高早餐怎么吃？',
  '尿酸高能吃豆制品吗？',
  '高血压一天盐摄入多少合适？',
  '推荐几道低GI主食',
]

const scrollToBottom = () => {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

const handleSend = async () => {
  const text = input.value.trim()
  if (!text || sending.value) return

  // 记录用户消息
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  scrollToBottom()

  // 占位的助手消息（加载态）
  messages.value.push({ role: 'assistant', content: '', loading: true })
  // 注意：必须取数组内的响应式代理来更新，直接用 push 前的原始对象不会触发视图刷新
  const placeholder = messages.value[messages.value.length - 1]
  sending.value = true
  scrollToBottom()

  try {
    // 携带历史（不含占位消息）
    const history = messages.value
      .filter(m => !m.loading && m.content)
      .slice(0, -1)
      .map(m => ({ role: m.role, content: m.content }))

    await streamChat(text, history, {
      onMeta: (sources) => { placeholder.sources = sources },
      onDelta: (delta) => {
        placeholder.loading = false
        placeholder.content += delta
        scrollToBottom()
      },
    })
  } catch (error) {
    placeholder.loading = false
    if (!placeholder.content) {
      placeholder.content = '抱歉，回答出错了，请稍后重试。'
    }
    console.error(error)
  } finally {
    placeholder.loading = false
    sending.value = false
    scrollToBottom()
  }
}

// SSE 流式请求：边生成边渲染
const streamChat = async (message, history, { onMeta, onDelta }) => {
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify({ message, history }),
  })
  if (resp.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('登录已过期')
  }
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `请求失败 ${resp.status}`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE 按空行分帧
    const frames = buffer.split('\n\n')
    buffer = frames.pop()
    for (const frame of frames) {
      const line = frame.replace(/^data: /, '').trim()
      if (!line) continue
      let payload
      try { payload = JSON.parse(line) } catch { continue }
      if (payload.type === 'meta') onMeta?.(payload.sources)
      else if (payload.type === 'delta') onDelta?.(payload.content)
      else if (payload.type === 'error') throw new Error(payload.detail || '生成中断')
    }
  }
}

const clearChat = () => {
  messages.value = []
}

onMounted(scrollToBottom)
</script>

<style scoped>
.dot {
  display: inline-block;
  font-size: 8px;
  color: #9ca3af;
}
</style>

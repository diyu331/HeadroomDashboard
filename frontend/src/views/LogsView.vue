<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">
        <i class="fas fa-list text-indigo-500 mr-2"></i>容器日志
      </h2>
      <div class="flex items-center gap-2">
        <span class="text-xs text-gray-400">{{ lineCount }}</span>
        <button @click="refreshLogs" :disabled="loading"
          class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition disabled:opacity-50">
          <i :class="['fas', loading ? 'fa-spinner fa-spin' : 'fa-sync-alt', 'text-xs']"></i>刷新
        </button>
        <button @click="downloadLogs"
          class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition">
          <i class="fas fa-download text-xs"></i>下载
        </button>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-center mb-6">
      <p class="text-red-600 text-sm">{{ error }}</p>
      <button @click="refreshLogs" class="mt-2 px-4 py-1.5 bg-red-100 text-red-700 rounded-lg text-sm hover:bg-red-200">重试</button>
    </div>

    <div class="bg-gray-900 rounded-xl p-4 border border-gray-700" style="min-height: 400px;">
      <pre v-if="loading && !lines.length"
        class="text-xs text-gray-500 font-mono whitespace-pre-wrap overflow-auto"
        style="max-height: 600px;">正在加载日志...</pre>
      <pre v-else-if="!lines.length"
        class="text-xs text-gray-500 font-mono whitespace-pre-wrap overflow-auto"
        style="max-height: 600px;">暂无日志</pre>
      <pre v-else
        class="text-xs text-gray-300 font-mono whitespace-pre-wrap overflow-auto"
        style="max-height: 600px;"
        v-html="renderedLogs"></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'

const showToast = inject('toast')
const lines = ref([])
const loading = ref(false)
const error = ref(null)

const lineCount = computed(() => lines.value.length + ' 行')

const renderedLogs = computed(() => {
  return lines.value.map(l => {
    const ts = l.slice(0, 30)
    const rest = l.slice(30)
    let color = 'text-gray-300'
    if (rest.includes('WARN') || rest.includes('warn')) color = 'text-yellow-300'
    if (rest.includes('ERROR') || rest.includes('error') || rest.includes('Error')) color = 'text-red-300'
    if (rest.includes('compression') || rest.includes('saved') || rest.includes('savings')) color = 'text-green-300'
    return `<div class="py-0.5 px-1 -mx-1 rounded"><span class="text-gray-500">${ts}</span><span class="${color}">${rest}</span></div>`
  }).join('')
})

async function refreshLogs() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/logs?lines=100')
    const data = await res.json()
    if (data.error) {
      error.value = data.error
      return
    }
    lines.value = (data.logs || '').split('\n').filter(Boolean)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function downloadLogs() {
  try {
    const res = await fetch('/api/logs?lines=500')
    const data = await res.json()
    const blob = new Blob([data.logs || ''], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `headroom-logs-${new Date().toISOString().slice(0, 19)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    showToast('下载失败: ' + e.message, 'error')
  }
}

refreshLogs()
</script>

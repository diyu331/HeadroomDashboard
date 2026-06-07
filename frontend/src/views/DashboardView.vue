<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">
        <i class="fas fa-chart-pie text-indigo-500 mr-2"></i>状态看板
      </h2>
      <div class="flex items-center gap-3">
        <span v-if="!loading" class="text-xs text-gray-400">{{ lastUpdate }}</span>
        <button @click="refresh" :disabled="loading"
          class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition disabled:opacity-50">
          <i :class="['fas', loading ? 'fa-spinner fa-spin' : 'fa-sync-alt', 'text-xs']"></i>刷新
        </button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-center mb-6">
      <p class="text-red-600 text-sm">{{ error }}</p>
      <button @click="refresh" class="mt-2 px-4 py-1.5 bg-red-100 text-red-700 rounded-lg text-sm hover:bg-red-200">重试</button>
    </div>

    <!-- Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <StatusCard title="运行状态" icon="fa-heartbeat">
        <template v-if="loading">
          <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
          <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2 mt-1.5"></div>
        </template>
        <template v-else-if="data">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full" :class="statusColor"></span>
            <span class="font-medium" :class="statusTextColor">{{ statusLabel }}</span>
          </div>
          <div class="text-gray-500">运行 {{ fmtTime(uptime) }}</div>
          <div class="text-gray-400 text-xs">v{{ versionText }} · {{ cidText }}</div>
        </template>
      </StatusCard>

      <StatusCard title="压缩统计" icon="fa-compress-alt">
        <template v-if="loading">
          <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
          <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2 mt-1.5"></div>
        </template>
        <template v-else-if="data">
          <div class="text-2xl font-bold text-gray-800">{{ fmtNum(allLayersSaved) }}</div>
          <div class="text-gray-500">总节省 Tokens</div>
          <div class="flex items-center gap-1.5">
            <span class="text-lg font-semibold text-green-600">{{ allLayersPct.toFixed(1) }}%</span>
            <span class="text-gray-400 text-xs">压缩率</span>
          </div>
        </template>
      </StatusCard>

      <StatusCard title="请求健康" icon="fa-heart-circle-check">
        <template v-if="loading">
          <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
          <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2 mt-1.5"></div>
        </template>
        <template v-else-if="data">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-lg font-semibold text-gray-800">{{ successRate }}%</div>
              <div class="text-gray-500">成功率</div>
            </div>
            <div class="text-right">
              <div class="text-lg font-semibold text-gray-800">{{ fmtNum(totalRequests) }}</div>
              <div class="text-gray-500 text-xs">总请求</div>
            </div>
          </div>
          <div class="flex items-center gap-3 text-xs pt-1">
            <span class="text-green-500">{{ fmtNum(cached) }} 缓存</span>
            <span :class="failed > 0 ? 'text-red-500' : 'text-gray-400'">{{ failed }} 失败</span>
            <span :class="rateLimited > 0 ? 'text-amber-500' : 'text-gray-400'">{{ rateLimited }} 限流</span>
          </div>
        </template>
      </StatusCard>

      <StatusCard title="请求概览" icon="fa-exchange-alt">
        <template v-if="loading">
          <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
          <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2 mt-1.5"></div>
        </template>
        <template v-else-if="data">
          <div class="text-2xl font-bold text-gray-800">{{ fmtNum(totalRequests) }}</div>
          <div class="text-gray-500">总请求</div>
          <div class="flex items-center gap-3 text-xs text-gray-500">
            <span><i class="fas fa-database mr-1"></i>{{ cacheHitRate }}</span>
            <span><i class="fas fa-clock mr-1"></i>{{ avgLatency }}</span>
          </div>
        </template>
      </StatusCard>
    </div>

    <!-- Container Controls -->
    <div class="bg-white rounded-xl p-5 border border-gray-200 mb-6">
      <h3 class="text-sm font-medium text-gray-700 mb-3">
        <i class="fas fa-server text-indigo-400 mr-2"></i>容器控制
      </h3>
      <div class="flex items-center gap-3">
        <button @click="containerAction('restart')" :disabled="actionLoading"
          class="px-4 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg hover:bg-amber-100 text-sm flex items-center gap-2 transition disabled:opacity-50">
          <i :class="['fas', actionLoading === 'restart' ? 'fa-spinner fa-spin' : 'fa-redo-alt']"></i>重启
        </button>
        <button @click="containerAction('stop')" :disabled="actionLoading"
          class="px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded-lg hover:bg-red-100 text-sm flex items-center gap-2 transition disabled:opacity-50">
          <i :class="['fas', actionLoading === 'stop' ? 'fa-spinner fa-spin' : 'fa-stop']"></i>停止
        </button>
        <button @click="containerAction('start')" :disabled="actionLoading"
          class="px-4 py-2 bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 text-sm flex items-center gap-2 transition disabled:opacity-50">
          <i :class="['fas', actionLoading === 'start' ? 'fa-spinner fa-spin' : 'fa-play']"></i>启动
        </button>
        <span v-if="actionResult" class="text-xs text-gray-400">{{ actionResult }}</span>
      </div>
    </div>

    <!-- Strategy Bars -->
    <div class="bg-white rounded-xl p-5 border border-gray-200 mb-6">
      <h3 class="text-sm font-medium text-gray-700 mb-3">
        <i class="fas fa-chart-bar text-indigo-400 mr-2"></i>压缩策略分布
      </h3>
      <div v-if="loading" class="space-y-2.5">
        <div class="animate-pulse h-5 bg-gray-200 rounded w-full"></div>
        <div class="animate-pulse h-5 bg-gray-200 rounded w-full"></div>
        <div class="animate-pulse h-5 bg-gray-200 rounded w-full"></div>
      </div>
      <div v-else-if="!strategyKeys.length" class="text-sm text-gray-400 py-4 text-center">
        暂无压缩数据（使用 Headroom 后才会产生）
      </div>
      <div v-else class="space-y-2.5">
        <div v-for="(key, i) in strategyKeys" :key="key" class="flex items-center gap-4">
          <span class="text-xs text-gray-500 w-36 text-right shrink-0 whitespace-nowrap">
            {{ strategyLabel(key) }}
          </span>
          <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500" :style="{ width: strategyPct(key) + '%', backgroundColor: COLORS[i % COLORS.length] }"></div>
          </div>
          <span class="text-xs font-medium text-gray-600 w-14 shrink-0 text-right">
            {{ strategyPct(key).toFixed(1) }}%
          </span>
          <span class="text-xs text-gray-400 w-20 shrink-0">{{ fmtNum(strategies[key]) }}</span>
        </div>
      </div>
    </div>

    <!-- Model Costs -->
    <div class="bg-white rounded-xl p-5 border border-gray-200">
      <h3 class="text-sm font-medium text-gray-700 mb-3">
        <i class="fas fa-calculator text-indigo-400 mr-2"></i>按模型压缩明细
      </h3>
      <div v-if="loading" class="space-y-3">
        <div class="animate-pulse h-20 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!modelKeys.length" class="text-sm text-gray-400 py-4 text-center">
        暂无数据（使用 Claude Code 后才会产生）
      </div>
      <div v-else class="space-y-3">
        <div v-for="key in modelKeys" :key="key" class="border border-gray-100 rounded-lg p-3.5">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-800">{{ models[key].name_cn || key }}</span>
              <span class="text-xs text-gray-400">{{ models[key].requests }} 次请求</span>
            </div>
            <span class="text-xs font-medium text-green-600">
              节省 {{ fmtNum(models[key].tokens_saved) }} · {{ (models[key].savings_percent || 0).toFixed(1) }}%
            </span>
          </div>
          <div class="relative h-6 bg-gray-100 rounded overflow-hidden">
            <div class="bg-indigo-300 h-full absolute top-0" :style="{ width: modelAfterPct(key) + '%' }"></div>
            <div class="bg-green-300 h-full absolute top-0" :style="{ left: modelAfterPct(key) + '%', width: (100 - modelAfterPct(key)) + '%' }"></div>
            <div class="absolute inset-0 flex items-center justify-between px-2 text-xs text-gray-700 font-medium">
              <span>压缩后 {{ fmtNum(models[key].input_tokens) }}</span>
              <span class="text-green-800">节省 {{ fmtNum(models[key].tokens_saved) }}</span>
            </div>
          </div>
          <div class="flex justify-between mt-1 text-xs text-gray-400">
            <span>压缩前 {{ fmtNum(models[key].total_before_compression) }}</span>
            <span>输出 {{ fmtNum(models[key].output_tokens) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import StatusCard from '../components/StatusCard.vue'

const showToast = inject('toast')

const data = ref(null)
const loading = ref(false)
const error = ref(null)
const lastUpdate = ref('')
const actionLoading = ref(null)
const actionResult = ref('')
const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#818cf8', '#7c3aed']

const STRATEGY_LABELS = {
  kompress: '智能压缩', ast: 'AST 压缩', json: 'JSON 压缩', cache: '缓存', prefix: '前缀缓存',
  cli_filtering: 'CLI 过滤', rtk: '精简上下文', lean_ctx: '精简上下文',
  text: '文本', log: '日志', search: '搜索', smart_crusher: '智能粉碎',
}

const container = computed(() => data.value?.container || {})
const health = computed(() => data.value?.health || {})
const stats = computed(() => data.value?.stats || {})
const models = computed(() => data.value?.model_costs?.per_model || {})
const modelKeys = computed(() => Object.keys(models.value))
const strategies = computed(() => stats.value?.compressions_by_strategy || {})
const strategyKeys = computed(() => Object.keys(strategies.value))

const statusColor = computed(() => isHealthy.value ? 'bg-green-500' : container.value.running ? 'bg-yellow-400' : 'bg-red-400')
const statusLabel = computed(() => isHealthy.value ? '健康' : container.value.running ? '启动中' : '已停止')
const statusTextColor = computed(() => isHealthy.value ? 'text-green-700' : container.value.running ? 'text-yellow-700' : 'text-red-700')

const isHealthy = computed(() => container.value.running && health.value?.status === 'healthy')
const uptime = computed(() => health.value?.uptime_seconds || 0)
const versionText = computed(() => health.value?.version || '-')
const cidText = computed(() => (container.value.container_id || '').slice(0, 12))
const allLayersSaved = computed(() => stats.value?.tokens?.all_layers_saved || 0)
const allLayersPct = computed(() => {
  const pct = stats.value?.tokens?.all_layers_savings_percent
  return pct != null ? pct : 0
})
const totalRequests = computed(() => stats.value?.requests?.total || 0)
const failed = computed(() => stats.value?.requests?.failed || 0)
const cached = computed(() => stats.value?.requests?.cached || 0)
const rateLimited = computed(() => stats.value?.requests?.rate_limited || 0)
const successRate = computed(() => totalRequests.value > 0 ? ((totalRequests.value - failed.value) / totalRequests.value * 100).toFixed(1) : '-')
const cacheHitRate = computed(() => stats.value?.compression_cache?.hit_rate != null ? stats.value.compression_cache.hit_rate.toFixed(1) + '%' : '-')
const avgLatency = computed(() => stats.value?.latency?.average_ms ? '~' + stats.value.latency.average_ms.toFixed(0) + 'ms' : '-')

function strategyLabel(key) { return STRATEGY_LABELS[key] || key }
function strategyPct(key) {
  const total = strategyKeys.value.reduce((s, k) => s + (strategies.value[k] || 0), 0)
  return total > 0 ? (strategies.value[key] || 0) / total * 100 : 0
}
function modelAfterPct(key) {
  const m = models.value[key]
  if (!m || !m.total_before_compression) return 50
  return Math.max(m.input_tokens / m.total_before_compression * 100, 5)
}
function fmtNum(n) {
  if (n == null || isNaN(n)) return '0'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}
function fmtTime(s) {
  if (!s) return '-'
  s = Number(s)
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}h${m}m` : `${m}m${Math.floor(s % 60)}s`
}

async function refresh() {
  loading.value = true
  error.value = null
  lastUpdate.value = '正在加载...'
  try {
    const res = await fetch('/api/stats')
    if (!res.ok) throw new Error('HTTP ' + res.status)
    data.value = await res.json()
    lastUpdate.value = new Date().toLocaleTimeString()
  } catch (e) {
    error.value = e.message
    lastUpdate.value = '加载失败'
    showToast('加载状态失败: ' + e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function containerAction(action) {
  const labels = { restart: '重启', stop: '停止', start: '启动' }
  actionLoading.value = action
  actionResult.value = `正在${labels[action]}...`
  try {
    const res = await fetch(`/api/container/${action}`, { method: 'POST' })
    const result = await res.json()
    if (result.success) {
      showToast(`容器已${labels[action]}`, 'success')
      await refresh()
      actionResult.value = ''
    } else {
      actionResult.value = `${labels[action]}失败: ${result.error || '未知错误'}`
      showToast(`${labels[action]}失败`, 'error')
    }
  } catch (e) {
    actionResult.value = `请求失败: ${e.message}`
    showToast(`请求失败: ${e.message}`, 'error')
  } finally {
    actionLoading.value = null
  }
}

refresh()
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">
        <i class="fas fa-cog text-indigo-500 mr-2"></i>配置中心
      </h2>
      <div class="flex items-center gap-2">
        <span class="text-xs text-gray-400">{{ saveStatus }}</span>
        <button @click="loadAll" class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition">
          <i class="fas fa-sync-alt text-xs"></i>刷新
        </button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-center mb-6">
      <p class="text-red-600 text-sm">{{ error }}</p>
      <button @click="loadAll" class="mt-2 px-4 py-1.5 bg-red-100 text-red-700 rounded-lg text-sm hover:bg-red-200">重试</button>
    </div>

    <!-- 系统环境配置 -->
    <div class="bg-white rounded-xl border border-gray-200 p-5 mb-4">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-medium text-gray-800"><i class="fas fa-globe text-indigo-400 mr-2"></i>系统环境配置</h3>
        <span v-if="!systemLoading" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" :class="routeBadge.class">
          <span class="w-1.5 h-1.5 rounded-full" :class="routeBadge.dot"></span>{{ routeBadge.text }}
        </span>
      </div>

      <div v-if="systemLoading" class="animate-pulse h-32 bg-gray-100 rounded"></div>

      <template v-else-if="systemData">
        <!-- 当前路由 -->
        <div class="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-100">
          <div class="text-xs text-gray-500 mb-2">当前路由</div>
          <div class="flex items-center justify-between">
            <div class="flex flex-col">
              <span class="text-sm font-mono text-gray-700">{{ systemData.anthropic_base_url || '(未配置)' }}</span>
              <span class="text-xs text-gray-400">{{ configSource }}</span>
            </div>
            <div class="flex items-center gap-2">
              <button @click="toggleRoute('headroom')" :disabled="toggleLoading"
                class="px-3 py-1.5 text-xs rounded-lg border transition flex items-center gap-1.5"
                :class="isHeadroom ? 'bg-indigo-500 text-white border-indigo-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'">
                <i class="fas fa-shield-alt"></i>Headroom 代理
              </button>
              <button @click="toggleRoute('direct')" :disabled="toggleLoading"
                class="px-3 py-1.5 text-xs rounded-lg border transition flex items-center gap-1.5"
                :class="isDirect ? 'bg-indigo-500 text-white border-indigo-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'">
                <i class="fas fa-plug"></i>直连 DeepSeek
              </button>
            </div>
          </div>
        </div>

        <!-- 表单 -->
        <div class="space-y-3">
          <div class="flex items-center py-1.5 border-b border-gray-100">
            <span class="w-48 shrink-0 text-sm text-gray-700"><i class="fas fa-route text-gray-400 w-4 mr-1.5"></i>自定义路由</span>
            <div class="flex-1">
              <select v-model="routeSelect" @change="onRouteSelect" :disabled="systemSaving"
                class="w-full p-1.5 border border-gray-300 rounded text-sm">
                <option value="http://localhost:8787">通过 Headroom 代理 (localhost:8787)</option>
                <option value="https://api.deepseek.com/anthropic">直连 DeepSeek</option>
                <option value="__custom__">自定义</option>
              </select>
            </div>
          </div>
          <div class="flex items-center py-1.5 border-b border-gray-100">
            <span class="w-48 shrink-0 text-sm text-gray-700"><i class="fas fa-link text-gray-400 w-4 mr-1.5"></i>ANTHROPIC_BASE_URL</span>
            <div class="flex-1">
              <input v-model="anthropicUrl" type="text" :disabled="systemSaving"
                placeholder="https://api.deepseek.com/anthropic"
                class="w-full p-1.5 border border-gray-300 rounded text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" />
            </div>
          </div>
          <div class="flex items-center py-1.5 border-b border-gray-100">
            <span class="w-48 shrink-0 text-sm text-gray-700"><i class="fas fa-file-code text-gray-400 w-4 mr-1.5"></i>配置位置</span>
            <div class="flex-1">
              <div class="flex flex-wrap gap-2 text-xs">
                <span v-for="loc in configLocations" :key="loc.label"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded"
                  :class="loc.active ? 'bg-indigo-50 text-indigo-600' : 'bg-gray-50 text-gray-400'">
                  <span class="w-1.5 h-1.5 rounded-full" :class="loc.active ? 'bg-indigo-400' : 'bg-gray-300'"></span>
                  {{ loc.label }}: {{ loc.value || '未设置' }}
                </span>
              </div>
            </div>
          </div>
          <div class="flex justify-end pt-2">
            <button @click="saveSystemConfig" :disabled="systemSaving"
              class="px-4 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600 disabled:opacity-50 transition flex items-center gap-2">
              <i :class="['fas', systemSaving ? 'fa-spinner fa-spin' : 'fa-save']"></i>保存系统配置
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- Headroom 代理参数 -->
    <div class="bg-white rounded-xl border border-gray-200 p-5 mb-4">
      <h3 class="text-base font-medium text-gray-800 mb-4">
        <i class="fas fa-sliders-h text-indigo-400 mr-2"></i>Headroom 代理参数
      </h3>

      <div v-if="paramsLoading" class="text-center py-8 text-gray-400">
        <i class="fas fa-spinner fa-spin mr-2"></i>加载参数...
      </div>

      <template v-else>
        <div v-for="cat in categories" :key="cat.key" class="mb-4">
          <h4 class="text-sm font-medium text-gray-600 mb-2">
            <i :class="['fas', cat.icon, 'text-indigo-300 mr-1.5']"></i>{{ cat.label }}
          </h4>
          <div v-for="p in getCategoryParams(cat.key)" :key="p.key" class="flex items-center py-1.5 border-b border-gray-100">
            <span class="w-48 shrink-0 text-sm text-gray-700">{{ p.label }}</span>
            <div class="flex-1">
              <!-- Bool -->
              <label v-if="p.type === 'bool'" class="toggle">
                <input type="checkbox" v-model="headroomForm[p.key]" />
                <span class="toggle-slider"></span>
              </label>
              <!-- Select -->
              <select v-else-if="p.type === 'select'" v-model="headroomForm[p.key]"
                class="w-full p-1.5 border border-gray-300 rounded text-sm">
                <option v-for="opt in p.options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <!-- Number -->
              <input v-else-if="p.type === 'number'" v-model.number="headroomForm[p.key]" type="number"
                :placeholder="p.placeholder || ''"
                class="w-full p-1.5 border border-gray-300 rounded text-sm focus:border-indigo-500 outline-none" />
              <!-- Text -->
              <input v-else v-model="headroomForm[p.key]" type="text" :placeholder="p.placeholder || ''"
                class="w-full p-1.5 border border-gray-300 rounded text-sm focus:border-indigo-500 outline-none" />
              <div v-if="p.description" class="text-xs text-gray-400 mt-1 leading-relaxed">{{ p.description }}</div>
            </div>
          </div>
        </div>

        <div class="flex justify-end pt-3 border-t border-gray-100 mt-3">
          <button @click="saveHeadroomConfig" :disabled="headroomSaving"
            class="px-4 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600 disabled:opacity-50 transition flex items-center gap-2">
            <i :class="['fas', headroomSaving ? 'fa-spinner fa-spin' : 'fa-redo-alt']"></i>
            {{ headroomBtnText }}
          </button>
        </div>
      </template>
    </div>

    <!-- 配置快照 -->
    <div class="bg-white rounded-xl border border-gray-200 p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-medium text-gray-800"><i class="fas fa-camera text-indigo-400 mr-2"></i>配置快照</h3>
        <button @click="loadSnapshot" class="text-xs text-indigo-500 hover:text-indigo-700">
          <i class="fas fa-sync-alt mr-1"></i>刷新
        </button>
      </div>
      <div v-if="snapshotLoading" class="animate-pulse h-12 bg-gray-100 rounded"></div>
      <div v-else-if="snapshot" class="space-y-2 text-xs text-gray-700">
        <div>
          <span class="font-medium">容器启动命令:</span>
          <pre class="mt-1 bg-gray-50 p-2 rounded text-xs overflow-x-auto">docker {{ snapshot.cmd }}</pre>
        </div>
        <div>
          <span class="font-medium">环境变量:</span>
          <pre class="mt-1 bg-gray-50 p-2 rounded text-xs overflow-x-auto">{{ snapshot.env }}</pre>
        </div>
        <div>
          <span class="font-medium">Profile 配置:</span>
          <pre class="mt-1 bg-gray-50 p-2 rounded text-xs overflow-x-auto">{{ snapshot.profileLines || '(未配置)' }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'

const showToast = inject('toast')
const saveStatus = ref('')
const error = ref(null)

const categories = [
  { key: 'mode', label: '运行模式', icon: 'fa-play-circle' },
  { key: 'optimization', label: '优化开关', icon: 'fa-toggle-on' },
  { key: 'memory', label: '记忆', icon: 'fa-brain' },
  { key: 'backend', label: '直连与后端', icon: 'fa-server' },
  { key: 'log', label: '预算与日志', icon: 'fa-chart-line' },
]

// ── System Config state ──
const systemData = ref(null)
const systemLoading = ref(false)
const systemSaving = ref(false)
const toggleLoading = ref(false)
const anthropicUrl = ref('')
const routeSelect = ref('')

// ── Headroom Config state ──
const configSchema = ref([])
const headroomForm = ref({})
const paramsLoading = ref(false)
const headroomSaving = ref(false)
const headroomBtnText = ref('保存并重启容器')

// ── Snapshot state ──
const snapshot = ref(null)
const snapshotLoading = ref(false)

// ── Computed ──
const isHeadroom = computed(() => (systemData.value?.anthropic_base_url || '').includes('localhost:8787'))
const isDirect = computed(() => (systemData.value?.anthropic_base_url || '').includes('api.deepseek.com'))

const routeBadge = computed(() => {
  if (isHeadroom.value) return { class: 'bg-green-50 text-green-700', dot: 'bg-green-500', text: 'Headroom 代理' }
  if (isDirect.value) return { class: 'bg-blue-50 text-blue-700', dot: 'bg-blue-500', text: '直连 DeepSeek' }
  const url = systemData.value?.anthropic_base_url
  if (url) return { class: 'bg-yellow-50 text-yellow-700', dot: 'bg-yellow-500', text: '自定义路由' }
  return { class: 'bg-gray-50 text-gray-500', dot: 'bg-gray-400', text: '未配置' }
})

const configSource = computed(() => {
  const parts = []
  if (systemData.value?.claude_settings_url) parts.push('settings.json ✓')
  if (systemData.value?.env_var) parts.push('系统环境变量 ✓')
  if (systemData.value?.profile_url) parts.push('profile.ps1 ✓')
  return parts.length ? '生效于: ' + parts.join(' · ') : '未配置'
})

const configLocations = computed(() => {
  const d = systemData.value
  return [
    { label: 'settings.json', value: d?.claude_settings_url || '未设置', active: !!d?.claude_settings_url },
    { label: '系统环境变量', value: d?.env_var || '未设置', active: !!d?.env_var },
    { label: 'profile.ps1', value: d?.profile_url || '未设置', active: !!d?.profile_url },
  ]
})

function getCategoryParams(catKey) {
  return configSchema.value.filter(p => p.category === catKey)
}

// ── System Config ──
async function loadSystemConfig() {
  try {
    const res = await fetch('/api/config/system')
    if (!res.ok) throw new Error('HTTP ' + res.status)
    systemData.value = await res.json()
    anthropicUrl.value = systemData.value.anthropic_base_url || ''
    const url = systemData.value.anthropic_base_url || ''
    const matched = ['http://localhost:8787', 'https://api.deepseek.com/anthropic'].includes(url)
    routeSelect.value = matched ? url : '__custom__'
  } catch (e) {
    showToast('加载系统配置失败: ' + e.message, 'error')
  }
}

function onRouteSelect() {
  if (routeSelect.value !== '__custom__') anthropicUrl.value = routeSelect.value
}

async function toggleRoute(route) {
  toggleLoading.value = true
  try {
    const res = await fetch('/api/config/system', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'toggle_route', route }),
    })
    const data = await res.json()
    if (data.success) {
      showToast(`已切换至 ${route === 'headroom' ? 'Headroom 代理' : '直连 DeepSeek'}，立即生效`, 'success')
      await loadSystemConfig()
    } else {
      showToast('切换失败: ' + (data.error || '未知错误'), 'error')
    }
  } catch (e) {
    showToast('请求失败: ' + e.message, 'error')
  } finally {
    toggleLoading.value = false
  }
}

async function saveSystemConfig() {
  const url = anthropicUrl.value.trim()
  if (!url) { showToast('请输入 ANTHROPIC_BASE_URL', 'error'); return }
  systemSaving.value = true
  try {
    const res = await fetch('/api/config/system', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'update_url', anthropic_base_url: url }),
    })
    const data = await res.json()
    if (data.success) {
      showToast(data.message, 'success')
      await loadSystemConfig()
    } else {
      showToast('保存失败: ' + (data.error || '未知错误'), 'error')
    }
  } catch (e) {
    showToast('请求失败: ' + e.message, 'error')
  } finally {
    systemSaving.value = false
  }
}

// ── Headroom Config ──
async function loadHeadroomParams() {
  try {
    const [listRes, curRes] = await Promise.all([
      fetch('/api/config/list'),
      fetch('/api/config/headroom'),
    ])
    if (!listRes.ok) throw new Error('HTTP ' + listRes.status)
    configSchema.value = await listRes.json()
    const current = await curRes.json()
    const form = {}
    for (const p of configSchema.value) {
      const env = current.env || {}
      const cmd = current.cmd || []
      let curVal = p.default
      if (p.key === 'anthropic-api-url' && env.ANTHROPIC_TARGET_API_URL) curVal = env.ANTHROPIC_TARGET_API_URL
      const idx = cmd.indexOf(p.flag === '-p' ? '-p' : p.flag)
      if (idx >= 0 && p.type !== 'bool') curVal = cmd[idx + 1] || curVal
      if (idx >= 0 && p.type === 'bool') curVal = true
      form[p.key] = curVal
    }
    headroomForm.value = form
  } catch (e) {
    showToast('加载参数失败: ' + e.message, 'error')
  }
}

async function saveHeadroomConfig() {
  headroomSaving.value = true
  headroomBtnText.value = '正在停止旧容器...'

  try {
    const res = await fetch('/api/config/headroom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(headroomForm.value),
    })
    const data = await res.json()
    if (!data.success) {
      showToast('容器重启失败: ' + (data.error || '未知错误'), 'error')
      return
    }

    headroomBtnText.value = '等待 Headroom 启动...'
    let ready = false
    for (let i = 0; i < 40; i++) {
      try {
        const hRes = await fetch('http://localhost:8787/health', { signal: AbortSignal.timeout(3000) })
        if (hRes.ok) { ready = true; break }
      } catch (_) {}
      headroomBtnText.value = `等待 Headroom 就绪 (${i + 1}/40 秒)...`
      await new Promise(r => setTimeout(r, 1000))
    }

    if (ready) {
      showToast('容器已重启，Headroom 就绪', 'success')
    } else {
      showToast('容器已重启，但 Headroom 仍未响应，请稍后手动刷新', 'warning')
    }
    await loadHeadroomParams()
  } catch (e) {
    showToast('保存失败: ' + e.message, 'error')
  } finally {
    headroomSaving.value = false
    headroomBtnText.value = '保存并重启容器'
  }
}

// ── Snapshot ──
async function loadSnapshot() {
  snapshotLoading.value = true
  try {
    const [sysRes, hrRes] = await Promise.all([
      fetch('/api/config/system'),
      fetch('/api/config/headroom'),
    ])
    const sys = await sysRes.json()
    const hr = await hrRes.json()
    const cmd = (hr.cmd || []).join(' ')
    const env = JSON.stringify(hr.env || {}, null, 2)
    const profileLines = (sys.profile_content || '').split('\n')
      .filter(l => l.includes('HEADROOM') || l.includes('ANTHROPIC_BASE_URL') || l.includes('headroom')).join('\n')
    snapshot.value = { cmd, env, profileLines }
  } catch (e) {
    snapshot.value = null
  } finally {
    snapshotLoading.value = false
  }
}

// ── Load All ──
async function loadAll() {
  error.value = null
  systemLoading.value = true
  paramsLoading.value = true
  try {
    await Promise.all([loadSystemConfig(), loadHeadroomParams(), loadSnapshot()])
  } catch (e) {
    error.value = e.message
  } finally {
    systemLoading.value = false
    paramsLoading.value = false
  }
}

loadAll()
</script>

<style scoped>
.toggle { position: relative; width: 44px; height: 24px; cursor: pointer; display: inline-block; }
.toggle input { display: none; }
.toggle-slider { position: absolute; inset: 0; background: #d1d5db; border-radius: 12px; transition: .3s; }
.toggle-slider::before { content: ''; position: absolute; width: 20px; height: 20px; left: 2px; bottom: 2px;
    background: white; border-radius: 50%; transition: .3s; }
.toggle input:checked + .toggle-slider { background: #6366f1; }
.toggle input:checked + .toggle-slider::before { transform: translateX(20px); }
</style>

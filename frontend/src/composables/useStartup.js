import { ref, onUnmounted } from 'vue'

const PHASES = [
  { key: 'docker_unavailable', icon: 'fa-triangle-exclamation', color: 'text-red-500',
    label: '检查 Docker 连接', error: true,
    action: '请启动 Docker Desktop 后重试' },
  { key: 'container_missing', icon: 'fa-spinner fa-spin', color: 'text-blue-500',
    label: '创建 Headroom 容器', error: false,
    action: '首次使用，正在拉取镜像并创建容器...' },
  { key: 'container_stopped', icon: 'fa-spinner fa-spin', color: 'text-blue-500',
    label: '启动 Headroom 容器', error: false,
    action: '正在启动...' },
  { key: 'waiting_headroom', icon: 'fa-spinner fa-spin', color: 'text-amber-500',
    label: '等待 Headroom 就绪', error: false,
    action: '服务初始化中...' },
  { key: 'ready', icon: 'fa-circle-check', color: 'text-green-500',
    label: 'Headroom 已就绪', error: false,
    action: '正在进入控制台...' },
]

export function useStartup() {
  const phase = ref('docker_checking')
  const detail = ref('正在连接...')
  const elapsed = ref(0)
  const maxWait = ref(120)
  let timer = null
  let pollTimer = null

  function getPhaseInfo(key) {
    return PHASES.find(p => p.key === key) || PHASES[0]
  }

  async function poll() {
    try {
      const res = await fetch('/api/startup/status')
      const data = await res.json()
      phase.value = data.phase
      detail.value = data.detail || ''
    } catch (e) {
      detail.value = '连接服务器中...'
    }
  }

  function start() {
    poll()
    pollTimer = setInterval(poll, 1000)
    timer = setInterval(() => {
      if (phase.value !== 'ready' && phase.value !== 'docker_unavailable') {
        elapsed.value++
      }
    }, 1000)
  }

  function stop() {
    if (timer) clearInterval(timer)
    if (pollTimer) clearInterval(pollTimer)
  }

  onUnmounted(stop)

  return { phase, detail, elapsed, maxWait, getPhaseInfo, start, stop }
}

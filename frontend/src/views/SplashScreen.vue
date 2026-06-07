<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center">
    <div class="w-full max-w-lg px-6">
      <!-- Logo -->
      <div class="text-center mb-10">
        <div class="w-16 h-16 mx-auto mb-4 rounded-xl bg-indigo-500 flex items-center justify-center">
          <span class="text-2xl font-bold text-white">H</span>
        </div>
        <h1 class="text-xl font-semibold text-white">Headroom Dashboard</h1>
        <p class="text-sm text-gray-400 mt-1">启动中，请稍候...</p>
      </div>

      <!-- Phases -->
      <div class="space-y-4">
        <div v-for="(phaseDef, index) in phaseList" :key="phaseDef.key"
          class="flex items-center gap-3 transition-opacity duration-300"
          :class="{ 'opacity-30': index > activeIndex }">

          <!-- Icon -->
          <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
            :class="getIconBg(phaseDef, index)">
            <i :class="['fas', phaseDef.icon, getIconClass(phaseDef, index)]"></i>
          </div>

          <!-- Label -->
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium"
              :class="index <= activeIndex ? 'text-gray-200' : 'text-gray-600'">
              {{ phaseDef.label }}
            </div>
            <div v-if="index === activeIndex && phaseDef.action" class="text-xs text-gray-500 mt-0.5">
              {{ phaseDef.action }}
            </div>
          </div>

          <!-- Status -->
          <div v-if="index < activeIndex" class="text-green-500 text-sm">&#10003;</div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div v-if="showProgress" class="mt-8">
        <div class="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div class="h-full bg-indigo-500 rounded-full transition-all duration-500 ease-linear"
            :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="flex justify-between text-xs text-gray-500 mt-2">
          <span>{{ detail }}</span>
          <span>{{ elapsed }} / {{ maxWait }}s</span>
        </div>
      </div>

      <!-- Error + Retry -->
      <div v-if="phase === 'docker_unavailable'" class="mt-8 text-center">
        <p class="text-red-400 text-sm mb-3">Docker Desktop 未运行</p>
        <button @click="retry"
          class="px-4 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600 transition">
          <i class="fas fa-redo-alt mr-1.5"></i>重试
        </button>
      </div>

      <!-- Timeout Warning -->
      <div v-if="elapsed > maxWait" class="mt-8 text-center">
        <p class="text-amber-400 text-sm mb-3">启动超时，请检查容器状态</p>
        <button @click="skip"
          class="px-4 py-2 bg-gray-600 text-white text-sm rounded-lg hover:bg-gray-500 transition">
          跳过，进入控制台
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useStartup } from '../composables/useStartup'

const emit = defineEmits(['ready'])
const { phase, detail, elapsed, maxWait, getPhaseInfo, start, stop } = useStartup()

const phaseKeys = ['docker_unavailable', 'container_missing', 'container_stopped', 'waiting_headroom', 'ready']
const phaseList = computed(() => phaseKeys.map(k => getPhaseInfo(k)))
const activeIndex = computed(() => {
  const idx = phaseKeys.indexOf(phase.value)
  return idx >= 0 ? idx : 0
})
const showProgress = computed(() =>
  ['waiting_headroom', 'container_stopped', 'container_missing'].includes(phase.value)
)
const progressPercent = computed(() =>
  Math.min(100, Math.round((elapsed.value / maxWait.value) * 100))
)

function getIconBg(phaseDef, index) {
  if (index < activeIndex.value) return 'bg-green-500/20'
  if (index === activeIndex.value) {
    if (phaseDef.error) return 'bg-red-500/20'
    return 'bg-indigo-500/20'
  }
  return 'bg-gray-700'
}

function getIconClass(phaseDef, index) {
  if (index < activeIndex.value) return 'text-green-500 !fa-circle-check'
  if (index === activeIndex.value && phaseDef.error) return 'text-red-400'
  if (index === activeIndex.value) return 'text-indigo-400'
  return 'text-gray-600'
}

function retry() {
  elapsed.value = 0
  start()
}

function skip() {
  stop()
  emit('ready')
}

onMounted(start)

watch(phase, (val) => {
  if (val === 'ready') {
    setTimeout(() => {
      stop()
      emit('ready')
    }, 800)
  }
})
</script>

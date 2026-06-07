<template>
  <div>
    <!-- Top Nav -->
    <nav class="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center">
              <span class="text-sm font-bold text-white">H</span>
            </div>
            <span class="text-lg font-semibold text-gray-900">Headroom Dashboard</span>
          </div>
          <div class="flex items-center gap-1">
            <router-link v-for="tab in tabs" :key="tab.path" :to="tab.path"
              class="px-4 py-2 text-sm rounded-lg transition"
              :class="$route.path === tab.path
                ? 'text-indigo-600 font-semibold bg-indigo-50'
                : 'text-gray-500 hover:bg-gray-100'">
              <i :class="['fas', tab.icon, 'mr-1.5']"></i>{{ tab.label }}
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <!-- Toast -->
    <div v-if="toast.show"
      class="fixed top-4 right-4 z-50 px-4 py-2.5 rounded-lg shadow-lg text-sm text-white flex items-center gap-2"
      :class="toastBg[toast.type] || 'bg-gray-700'"
      style="animation: slideIn .3s ease, fadeOut .3s ease 2.7s forwards;">
      <i :class="['fas', toastIcons[toast.type] || 'fa-info-circle']"></i>
      {{ toast.message }}
    </div>

    <!-- Page Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { reactive, provide } from 'vue'

const tabs = [
  { path: '/', label: '状态', icon: 'fa-chart-pie' },
  { path: '/config', label: '配置', icon: 'fa-cog' },
  { path: '/logs', label: '日志', icon: 'fa-list' },
]

const toast = reactive({ show: false, message: '', type: 'success' })
const toastBg = { success: 'bg-green-500', error: 'bg-red-500', info: 'bg-blue-500', warning: 'bg-amber-500' }
const toastIcons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' }
let toastTimer = null

function showToast(message, type = 'success') {
  toast.show = true
  toast.message = message
  toast.type = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.show = false }, 3000)
}

provide('toast', showToast)
</script>

<style scoped>
@keyframes slideIn { from { transform: translateY(-100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes fadeOut { to { opacity: 0; transform: translateY(-20px); } }
</style>

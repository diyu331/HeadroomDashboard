<template>
  <div class="card bg-white rounded-xl p-5 border border-gray-200 hover:shadow-md transition-shadow">
    <div class="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wider mb-3">
      <i :class="['fas', icon]"></i><span>{{ title }}</span>
    </div>
    <div class="space-y-1.5 text-sm">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  icon: { type: String, required: true },
})
</script>

<template>
  <SplashScreen v-if="startupPhase !== 'ready'" @ready="startupPhase = 'ready'" />
  <MainLayout v-else />
</template>

<script setup>
import { ref } from 'vue'
import SplashScreen from './views/SplashScreen.vue'
import MainLayout from './views/MainLayout.vue'

const startupPhase = ref('docker_checking')
</script>

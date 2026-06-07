import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

const routes = [
  { path: '/', component: () => import('./views/DashboardView.vue') },
  { path: '/config', component: () => import('./views/ConfigView.vue') },
  { path: '/logs', component: () => import('./views/LogsView.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

createApp(App).use(router).mount('#app')

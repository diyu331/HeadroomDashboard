import { ref, onMounted } from 'vue'

export function useApi(fetchFn, options = {}) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      data.value = await fetchFn()
    } catch (e) {
      error.value = e.message || '请求失败'
    } finally {
      loading.value = false
    }
  }

  if (options.immediate !== false) {
    onMounted(refresh)
  }

  return { data, loading, error, refresh }
}

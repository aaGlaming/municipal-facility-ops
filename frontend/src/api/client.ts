import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 90_000,
})

api.interceptors.request.use((config) => {
  config.headers.set('X-Request-Id', crypto.randomUUID())
  return config
})

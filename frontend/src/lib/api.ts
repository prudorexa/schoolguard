/**
 * Central axios instance.
 *
 * - Attaches the access token to every request.
 * - On a 401, tries one silent refresh via /auth/token/refresh/ before
 *   giving up and forcing a re-login. This is the only place token logic
 *   lives — features never touch localStorage or refresh logic directly.
 */
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const ACCESS_TOKEN_KEY = 'sg_access_token'
const REFRESH_TOKEN_KEY = 'sg_refresh_token'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access)
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

export const api = axios.create({
  baseURL: '/api/v1',
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) return null
  try {
    const { data } = await axios.post('/api/v1/auth/token/refresh/', { refresh })
    tokenStorage.set(data.access, refresh)
    return data.access as string
  } catch {
    tokenStorage.clear()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true
      refreshing ??= refreshAccessToken()
      const newAccess = await refreshing
      refreshing = null
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`
        return api(original)
      }
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

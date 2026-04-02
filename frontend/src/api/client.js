import axios from 'axios'
import { useAuth } from '@clerk/react'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Returns an axios instance that automatically attaches the Clerk Bearer token
 * to every request. Must be called inside a React component or hook.
 */
// Single shared instance — interceptor is added once and closes over a ref
// to the latest getToken, so it never goes stale across re-renders.
const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

let _getToken = null
apiClient.interceptors.request.use(async (config) => {
  if (_getToken) {
    const token = await _getToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function useApiClient() {
  const { getToken } = useAuth()
  _getToken = getToken
  return apiClient
}

/**
 * Unauthenticated client for public endpoints (payment portal).
 * Safe to import as a plain module — no Clerk dependency.
 */
const publicClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export default publicClient

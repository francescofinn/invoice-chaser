import axios from 'axios'
import { useAuth } from '@clerk/react'
import { useMemo } from 'react'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Returns an axios instance that automatically attaches the Clerk Bearer token
 * to every request. Must be called inside a React component or hook.
 */
export function useApiClient() {
  const { getToken } = useAuth()

  const client = useMemo(() => {
    const instance = axios.create({
      baseURL: BASE_URL,
      headers: { 'Content-Type': 'application/json' },
    })

    instance.interceptors.request.use(async (config) => {
      const token = await getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    return instance
  }, [getToken])

  return client
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

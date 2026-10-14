import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

import { api, tokenStorage } from "./api"
import type { Me } from "../types/api"

interface AuthContextValue {
  user: Me | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  async function fetchMe() {
    try {
      const { data } = await api.get<Me>("/auth/me/")
      setUser(data)
    } catch {
      setUser(null)
    }
  }

  useEffect(() => {
    if (tokenStorage.getAccess()) {
      fetchMe().finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  async function login(email: string, password: string) {
    const { data } = await api.post<{ access: string; refresh: string }>("/auth/token/", { email, password })
    tokenStorage.set(data.access, data.refresh)
    await fetchMe()
  }

  function logout() {
    tokenStorage.clear()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

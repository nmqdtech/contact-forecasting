import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserOut } from '../api/auth'

interface AuthState {
  token: string | null
  user: UserOut | null
  setAuth: (token: string, user: UserOut) => void
  logout: () => void
  clearMustChangePassword: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      clearMustChangePassword: () =>
        set((s) =>
          s.user ? { user: { ...s.user, must_change_password: false } } : {}
        ),
    }),
    { name: 'forecasting-auth' }
  )
)

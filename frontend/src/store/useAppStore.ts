import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  theme: 'light' | 'dark'
  activeDatasetId: string | null
  selectedChannel: string | null
  activeJobId: string | null
  toggleTheme: () => void
  setActiveDatasetId: (id: string | null) => void
  setSelectedChannel: (channel: string | null) => void
  setActiveJobId: (id: string | null) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      activeDatasetId: null,
      selectedChannel: null,
      activeJobId: null,
      toggleTheme: () =>
        set({ theme: get().theme === 'light' ? 'dark' : 'light' }),
      setActiveDatasetId: (id) => set({ activeDatasetId: id }),
      setSelectedChannel: (channel) => set({ selectedChannel: channel }),
      setActiveJobId: (id) => set({ activeJobId: id }),
    }),
    { name: 'forecasting-app' }
  )
)

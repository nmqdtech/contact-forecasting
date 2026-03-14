import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ChartSettings {
  historicalColor: string
  forecastColor: string
  showDataLabels: boolean
  yAxisScale: 'auto' | 'log'
}

interface AppState {
  theme: 'light' | 'dark'
  activeDatasetId: string | null
  selectedChannel: string | null
  activeJobId: string | null
  activeProjectId: string | null
  chartSettings: ChartSettings
  toggleTheme: () => void
  setActiveDatasetId: (id: string | null) => void
  setSelectedChannel: (channel: string | null) => void
  setActiveJobId: (id: string | null) => void
  setActiveProjectId: (id: string | null) => void
  setChartSettings: (patch: Partial<ChartSettings>) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      activeDatasetId: null,
      selectedChannel: null,
      activeJobId: null,
      activeProjectId: null,
      chartSettings: {
        historicalColor: '#2563EB',
        forecastColor: '#F59E0B',
        showDataLabels: false,
        yAxisScale: 'auto',
      },
      toggleTheme: () =>
        set({ theme: get().theme === 'light' ? 'dark' : 'light' }),
      setActiveDatasetId: (id) => set({ activeDatasetId: id }),
      setSelectedChannel: (channel) => set({ selectedChannel: channel }),
      setActiveJobId: (id) => set({ activeJobId: id }),
      setActiveProjectId: (id) => set({ activeProjectId: id }),
      setChartSettings: (patch) =>
        set((s) => ({ chartSettings: { ...s.chartSettings, ...patch } })),
    }),
    { name: 'forecasting-app' }
  )
)

import { useQuery } from '@tanstack/react-query'
import {
  getBacktest,
  getForecast,
  getMonthlyForecast,
  getSeasonality,
  getSummary,
} from '../api/forecasts'
import { useAppStore } from '../store/useAppStore'

export function useForecast(channel: string | null) {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['forecast', channel, projectId],
    queryFn: () => getForecast(channel!, projectId),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useMonthlyForecast(channel: string | null) {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['forecast-monthly', channel, projectId],
    queryFn: () => getMonthlyForecast(channel!, projectId),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useBacktest(channel: string | null) {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['backtest', channel, projectId],
    queryFn: () => getBacktest(channel!, projectId),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useSeasonality(channel: string | null) {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['seasonality', channel, projectId],
    queryFn: () => getSeasonality(channel!, projectId),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useSummary() {
  return useQuery({
    queryKey: ['summary'],
    queryFn: getSummary,
    staleTime: 30_000,
  })
}

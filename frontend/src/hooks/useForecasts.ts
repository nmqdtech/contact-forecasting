import { useQuery } from '@tanstack/react-query'
import {
  getBacktest,
  getForecast,
  getMonthlyForecast,
  getSeasonality,
  getSummary,
} from '../api/forecasts'

export function useForecast(channel: string | null) {
  return useQuery({
    queryKey: ['forecast', channel],
    queryFn: () => getForecast(channel!),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useMonthlyForecast(channel: string | null) {
  return useQuery({
    queryKey: ['forecast-monthly', channel],
    queryFn: () => getMonthlyForecast(channel!),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useBacktest(channel: string | null) {
  return useQuery({
    queryKey: ['backtest', channel],
    queryFn: () => getBacktest(channel!),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useSeasonality(channel: string | null) {
  return useQuery({
    queryKey: ['seasonality', channel],
    queryFn: () => getSeasonality(channel!),
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

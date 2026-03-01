import client from './client'
import type {
  BacktestResponse,
  ForecastResponse,
  MonthlyForecastResponse,
  SeasonalityResponse,
  SummaryRow,
} from '../types'

export const getForecast = async (channel: string): Promise<ForecastResponse> => {
  const { data } = await client.get<ForecastResponse>(
    `/forecasts/${encodeURIComponent(channel)}`
  )
  return data
}

export const getMonthlyForecast = async (channel: string): Promise<MonthlyForecastResponse> => {
  const { data } = await client.get<MonthlyForecastResponse>(
    `/forecasts/${encodeURIComponent(channel)}/monthly`
  )
  return data
}

export const getBacktest = async (channel: string): Promise<BacktestResponse> => {
  const { data } = await client.get<BacktestResponse>(
    `/forecasts/${encodeURIComponent(channel)}/backtest`
  )
  return data
}

export const getSeasonality = async (channel: string): Promise<SeasonalityResponse> => {
  const { data } = await client.get<SeasonalityResponse>(
    `/seasonality/${encodeURIComponent(channel)}`
  )
  return data
}

export const getSummary = async (): Promise<SummaryRow[]> => {
  const { data } = await client.get<SummaryRow[]>('/summary')
  return data
}

/** Returns a URL string for direct browser download */
export const exportForecastsUrl = (channels?: string[]): string => {
  const params = channels?.map((c) => `channels=${encodeURIComponent(c)}`).join('&')
  return `/api/v1/exports/forecasts${params ? `?${params}` : ''}`
}

export const exportSummaryUrl = (): string => '/api/v1/exports/summary'

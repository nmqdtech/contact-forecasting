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

async function fetchBlob(url: string, filename: string) {
  const res = await client.get(url, { responseType: 'blob' })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

export const downloadForecasts = (channels?: string[]) => {
  const params = channels?.map((c) => `channels=${encodeURIComponent(c)}`).join('&')
  const url = `/exports/forecasts${params ? `?${params}` : ''}`
  return fetchBlob(url, 'forecasts.xlsx')
}

export const downloadSummary = () => fetchBlob('/exports/summary', 'summary.xlsx')

export const downloadReport = () => fetchBlob('/exports/report', 'forecast-report.pdf')

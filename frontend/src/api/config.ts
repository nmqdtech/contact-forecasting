import client from './client'
import type { ConfigResponse, HolidayConfigRequest, MonthlyTargetsRequest } from '../types'

export const getConfig = async (): Promise<ConfigResponse> => {
  const { data } = await client.get<ConfigResponse>('/config')
  return data
}

export const setHoliday = async (req: HolidayConfigRequest): Promise<void> => {
  await client.put('/config/holidays', req)
}

export const deleteHoliday = async (channel: string): Promise<void> => {
  await client.delete(`/config/holidays/${encodeURIComponent(channel)}`)
}

export const setTargets = async (req: MonthlyTargetsRequest): Promise<void> => {
  await client.put('/config/targets', req)
}

export const deleteTargets = async (channel: string): Promise<void> => {
  await client.delete(`/config/targets/${encodeURIComponent(channel)}`)
}

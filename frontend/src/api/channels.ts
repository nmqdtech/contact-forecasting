import client from './client'
import type { ChannelInfo, HourlyPoint, MonthlyObservation, ObservationPoint } from '../types'

export const getChannels = async (): Promise<ChannelInfo[]> => {
  const { data } = await client.get<ChannelInfo[]>('/channels')
  return data
}

export const getChannelData = async (channel: string): Promise<ObservationPoint[]> => {
  const { data } = await client.get<ObservationPoint[]>(
    `/channels/${encodeURIComponent(channel)}/data`
  )
  return data
}

export const getChannelMonthly = async (channel: string): Promise<MonthlyObservation[]> => {
  const { data } = await client.get<MonthlyObservation[]>(
    `/channels/${encodeURIComponent(channel)}/monthly`
  )
  return data
}

export const getChannelHourly = async (channel: string): Promise<HourlyPoint[]> => {
  const { data } = await client.get<HourlyPoint[]>(
    `/channels/${encodeURIComponent(channel)}/hourly`
  )
  return data
}

import client from './client'
import type { ChannelInfo, HourlyPoint, MonthlyObservation, ObservationPoint } from '../types'

export const getChannels = async (projectId?: string | null): Promise<ChannelInfo[]> => {
  const { data } = await client.get<ChannelInfo[]>('/channels', {
    params: projectId ? { project_id: projectId } : undefined,
  })
  return data
}

export const getChannelData = async (
  channel: string,
  projectId?: string | null
): Promise<ObservationPoint[]> => {
  const { data } = await client.get<ObservationPoint[]>(
    `/channels/${encodeURIComponent(channel)}/data`,
    { params: projectId ? { project_id: projectId } : undefined }
  )
  return data
}

export const getChannelMonthly = async (
  channel: string,
  projectId?: string | null
): Promise<MonthlyObservation[]> => {
  const { data } = await client.get<MonthlyObservation[]>(
    `/channels/${encodeURIComponent(channel)}/monthly`,
    { params: projectId ? { project_id: projectId } : undefined }
  )
  return data
}

export const getChannelHourly = async (
  channel: string,
  projectId?: string | null
): Promise<HourlyPoint[]> => {
  const { data } = await client.get<HourlyPoint[]>(
    `/channels/${encodeURIComponent(channel)}/hourly`,
    { params: projectId ? { project_id: projectId } : undefined }
  )
  return data
}

import type { HiringWave, HiringWaveCreate } from '../types'
import client from './client'

export const listHiringWaves = async (channel?: string): Promise<HiringWave[]> => {
  const url = channel ? `/hiring-waves/${encodeURIComponent(channel)}` : '/hiring-waves'
  const { data } = await client.get<HiringWave[]>(url)
  return data
}

export const createHiringWave = async (body: HiringWaveCreate): Promise<HiringWave> => {
  const { data } = await client.post<HiringWave>('/hiring-waves', body)
  return data
}

export const deleteHiringWave = async (id: string): Promise<void> => {
  await client.delete(`/hiring-waves/${id}`)
}

import client from './client'
import type { DatasetOut, DatasetSummary } from '../types'

export const uploadFile = async (file: File): Promise<DatasetOut> => {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<DatasetOut>('/uploads', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const listDatasets = async (): Promise<DatasetSummary[]> => {
  const { data } = await client.get<DatasetSummary[]>('/uploads')
  return data
}

export const deleteDataset = async (id: string): Promise<void> => {
  await client.delete(`/uploads/${id}`)
}

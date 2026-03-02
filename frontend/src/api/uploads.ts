import client from './client'
import type { DatasetOut, DatasetSummary } from '../types'

export const uploadFiles = async (files: File[]): Promise<DatasetOut> => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const { data } = await client.post<DatasetOut>('/uploads', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/** @deprecated Use uploadFiles instead */
export const uploadFile = async (file: File): Promise<DatasetOut> =>
  uploadFiles([file])

export const listDatasets = async (): Promise<DatasetSummary[]> => {
  const { data } = await client.get<DatasetSummary[]>('/uploads')
  return data
}

export const deleteDataset = async (id: string): Promise<void> => {
  await client.delete(`/uploads/${id}`)
}

export const resetAllData = async (): Promise<void> => {
  await client.delete('/uploads/reset')
}

import client from './client'
import type { DatasetOut, DatasetSummary } from '../types'

export const uploadFiles = async (
  files: File[],
  opts?: { projectId?: string | null; isActuals?: boolean }
): Promise<DatasetOut> => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const params: Record<string, string> = {}
  if (opts?.projectId) params.project_id = opts.projectId
  if (opts?.isActuals) params.is_actuals = 'true'
  const { data } = await client.post<DatasetOut>('/uploads', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: Object.keys(params).length ? params : undefined,
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

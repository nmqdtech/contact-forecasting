import client from './client'
import type { TrainingJobStatus, TrainingRequest } from '../types'

export const startTraining = async (
  req: TrainingRequest
): Promise<{ job_id: string; status: string }> => {
  const { data } = await client.post('/training', req)
  return data
}

export const getJobStatus = async (jobId: string): Promise<TrainingJobStatus> => {
  const { data } = await client.get<TrainingJobStatus>(`/training/${jobId}`)
  return data
}

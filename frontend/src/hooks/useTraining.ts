import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getJobStatus, startTraining } from '../api/training'
import { useAppStore } from '../store/useAppStore'
import type { TrainingJobStatus } from '../types'

export function useTrainingStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['training-job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as TrainingJobStatus | undefined
      if (!data) return 2000
      return data.status === 'pending' || data.status === 'running' ? 2000 : false
    },
  })
}

export function useStartTraining() {
  const queryClient = useQueryClient()
  const setActiveJobId = useAppStore((s) => s.setActiveJobId)

  return useMutation({
    mutationFn: startTraining,
    onSuccess: (data) => {
      setActiveJobId(data.job_id)
    },
    onSettled: () => {
      // After job completes polling will stop; also refresh downstream queries
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['channels'] })
        queryClient.invalidateQueries({ queryKey: ['summary'] })
      }, 3000)
    },
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteHoliday,
  deleteTargets,
  getConfig,
  setHoliday,
  setTargets,
} from '../api/config'
import type { HolidayConfigRequest, MonthlyTargetsRequest } from '../types'

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
    staleTime: 30_000,
  })
}

export function useSetHoliday() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: HolidayConfigRequest) => setHoliday(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config'] }),
  })
}

export function useDeleteHoliday() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (channel: string) => deleteHoliday(channel),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config'] }),
  })
}

export function useSetTargets() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: MonthlyTargetsRequest) => setTargets(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config'] }),
  })
}

export function useDeleteTargets() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (channel: string) => deleteTargets(channel),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config'] }),
  })
}

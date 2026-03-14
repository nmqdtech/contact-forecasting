import { useQuery } from '@tanstack/react-query'
import { getChannelData, getChannelHourly, getChannels } from '../api/channels'
import { useAppStore } from '../store/useAppStore'

export function useChannels() {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['channels', projectId],
    queryFn: () => getChannels(projectId),
    staleTime: 30_000,
  })
}

export function useChannelData(channel: string | null) {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['channel-data', channel, projectId],
    queryFn: () => getChannelData(channel!, projectId),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

export function useChannelHourly(channel: string | null) {
  const projectId = useAppStore((s) => s.activeProjectId)
  return useQuery({
    queryKey: ['channel-hourly', channel, projectId],
    queryFn: () => getChannelHourly(channel!, projectId),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

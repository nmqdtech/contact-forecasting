import { useQuery } from '@tanstack/react-query'
import { getChannelData, getChannels } from '../api/channels'

export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: getChannels,
    staleTime: 30_000,
  })
}

export function useChannelData(channel: string | null) {
  return useQuery({
    queryKey: ['channel-data', channel],
    queryFn: () => getChannelData(channel!),
    enabled: !!channel,
    staleTime: 60_000,
  })
}

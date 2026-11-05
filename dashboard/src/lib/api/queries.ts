import { useQuery } from '@tanstack/react-query'
import { api, qk } from './client'

export const useOverview = () => useQuery({ queryKey: qk.overview(), queryFn: () => api.overview() })
export const useDesk = () => useQuery({ queryKey: qk.desk, queryFn: api.desk })
export const useAsks = () => useQuery({ queryKey: qk.asks, queryFn: () => api.asks() })
export const useAsk = (id: string | null) =>
  useQuery({ queryKey: qk.ask(id ?? ''), queryFn: () => api.ask(id ?? ''), enabled: Boolean(id) })
export const useChangeRequests = () => useQuery({ queryKey: qk.changeRequests, queryFn: api.changeRequests })
export const useChangeRequest = (id: string | null) =>
  useQuery({ queryKey: qk.changeRequest(id ?? ''), queryFn: () => api.changeRequest(id ?? ''), enabled: Boolean(id) })
export const useEvents = () => useQuery({ queryKey: qk.events, queryFn: () => api.events() })
export const useScope = () => useQuery({ queryKey: qk.scope, queryFn: api.scope, staleTime: Infinity })
export const usePlan = () => useQuery({ queryKey: qk.plan, queryFn: api.plan })
export const useRooms = () => useQuery({ queryKey: qk.rooms, queryFn: api.rooms })

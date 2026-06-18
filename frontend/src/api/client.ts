import axios from 'axios'
import type { Ticket, TriageResponse, TriageResult } from '../types/ticket'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000, // 2 min for bulk Excel uploads
})

export async function triageSingle(ticket: Ticket): Promise<TriageResponse> {
  const { data } = await api.post<TriageResponse>('/triage/single', ticket)
  return data
}

export async function triageExcel(file: File): Promise<TriageResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<TriageResponse>('/triage/excel', form)
  return data
}

export async function getResult(ticketId: string): Promise<TriageResult> {
  const { data } = await api.get<TriageResult>(`/triage/${ticketId}`)
  return data
}

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await api.get('/health')
  return data
}

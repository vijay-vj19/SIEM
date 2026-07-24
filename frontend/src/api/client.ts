import axios from 'axios'
import type { Ticket, TriageResponse, TriageResult } from '../types/ticket'
import type { LangSmithRange, LangSmithRunsResponse, LangSmithSummary } from '../types/langsmith'
import type { ModelComparisonResponse } from '../types/modelComparison'
import type { LiveComparisonResponse } from '../types/liveComparison'
import { DASHBOARD_TIMEZONE } from '../lib/timezone'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
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

export async function downloadResultPdf(ticketId: string): Promise<Blob> {
  const { data } = await api.get(`/triage/${ticketId}/pdf`, { responseType: 'blob' })
  return data
}

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await api.get('/health')
  return data
}

export async function getLangsmithSummary(range: LangSmithRange): Promise<LangSmithSummary> {
  const { data } = await api.get<LangSmithSummary>('/langsmith/summary', {
    params: { range, tz: DASHBOARD_TIMEZONE },
  })
  return data
}

export async function getLangsmithRuns(range: LangSmithRange, limit = 50): Promise<LangSmithRunsResponse> {
  const { data } = await api.get<LangSmithRunsResponse>('/langsmith/runs', { params: { range, limit } })
  return data
}

export async function getModelComparison(): Promise<ModelComparisonResponse> {
  const { data } = await api.get<ModelComparisonResponse>('/model-comparison')
  return data
}

export async function predictExcelAllModels(file: File): Promise<LiveComparisonResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<LiveComparisonResponse>('/model-comparison/predict-excel', form)
  return data
}

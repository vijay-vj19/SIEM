export type LangSmithRange = '24h' | '7d' | '30d'

export interface RunsOverTimeBucket {
  bucket: string
  count: number
}

export interface LangSmithSummary {
  configured: boolean
  error?: string | null
  total_runs: number
  error_count: number
  error_rate: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  runs_over_time: RunsOverTimeBucket[]
}

export interface LangSmithRun {
  run_id: string
  ticket_id: string | null
  status: 'success' | 'error'
  latency_ms: number
  total_tokens: number
  cost_usd: number
  started_at: string
  langsmith_url: string | null
}

export interface LangSmithRunsResponse {
  configured: boolean
  error?: string | null
  runs: LangSmithRun[]
}

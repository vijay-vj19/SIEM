export interface Ticket {
  ticket_id: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: string
  created_time: string
  rule_triggered: string
  mitre_attack: string
  user: string
  user_type: 'service_account' | 'standard_user' | 'admin_user'
  source_asset: string
  source_ip: string
  target_asset: string
  target_ip: string
  process: string
  command_line: string
  decoded_command: string
  hour_of_day: number
  day_of_week: string
  historical_tp_count: number
  historical_fp_count: number
}

export interface SimilarIncident {
  ticket_id: string
  similarity: number
  verdict: string
}

export interface GuardrailStatus {
  presidio_pii_scan: string
  nemo_input_rail: string
  nemo_output_rail: string
}

export interface TriageResult {
  ticket_id: string
  verdict: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NEEDS_REVIEW'
  confidence: number
  xgboost_score: number
  llm_reasoning: string
  root_cause?: string
  contributing_factors?: string[]
  mitre_attack: string
  risk_score: number
  sir_report: string
  processing_time_ms: number
  similar_past_incidents: SimilarIncident[]
  guardrail_status?: GuardrailStatus
}

export interface TriageSummary {
  total: number
  true_positive: number
  false_positive: number
  needs_review: number
}

export interface TriageResponse {
  results: TriageResult[]
  summary: TriageSummary
  errors?: { row: number; ticket_id: string; error: string }[]
}

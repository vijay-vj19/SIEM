export interface LiveComparisonTicket {
  ticket_id: string
  predictions: Record<string, string>
  unanimous: boolean
  true_label?: string
}

export interface AccuracyPerModel {
  correct: number
  total: number
  accuracy: number
  f1_macro: number
  f1_per_class: {
    FALSE_POSITIVE: number
    NEEDS_REVIEW: number
    TRUE_POSITIVE: number
  }
}

export interface LiveComparisonResponse {
  has_labels: boolean
  total_tickets: number
  unanimous_count: number
  unanimous_rate: number
  tickets: LiveComparisonTicket[]
  accuracy_per_model?: Record<string, AccuracyPerModel>
}

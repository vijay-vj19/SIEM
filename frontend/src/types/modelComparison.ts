export interface ModelComparisonResult {
  name: string
  accuracy_mean: number
  accuracy_std: number
  precision_macro: number
  recall_macro: number
  f1_macro: number
  confusion_matrix: number[][]
  confusion_matrix_labels: string[]
  train_time_sec_mean: number
  inference_ms_per_ticket_mean: number
  model_size_kb: number
}

export interface ModelComparisonResponse {
  dataset_rows: number
  n_splits: number
  disclosure: string
  results: ModelComparisonResult[]
}

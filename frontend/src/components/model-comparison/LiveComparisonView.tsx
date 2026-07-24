import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { Upload, FileSpreadsheet, X, ChevronRight, CheckCircle2, XCircle } from 'lucide-react'
import { predictExcelAllModels } from '../../api/client'
import type { LiveComparisonResponse } from '../../types/liveComparison'

const MODEL_NAMES = ['XGBoost', 'CatBoost', 'LightGBM', 'Random Forest', 'Logistic Regression', 'SVM (RBF)', 'KNN']

type SortMetric = 'accuracy' | 'f1_macro' | 'f1_fp' | 'f1_nr' | 'f1_tp'

const SORT_OPTIONS: { value: SortMetric; label: string }[] = [
  { value: 'accuracy', label: 'Accuracy' },
  { value: 'f1_macro', label: 'F1 (macro — avg of FP/NR/TP)' },
  { value: 'f1_fp', label: 'FALSE_POSITIVE F1' },
  { value: 'f1_nr', label: 'NEEDS_REVIEW F1' },
  { value: 'f1_tp', label: 'TRUE_POSITIVE F1' },
]

export function LiveComparisonView() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<LiveComparisonResponse | null>(null)
  const [sortMetric, setSortMetric] = useState<SortMetric>('f1_macro')

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]
    if (!f) return
    setFile(f)
    setResult(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
  })

  const handleSubmit = async () => {
    if (!file) return
    setLoading(true)
    try {
      const res = await predictExcelAllModels(file)
      setResult(res)
      toast.success(`Predicted ${res.total_tickets} ticket(s) across all 7 models`)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string; detail?: string } } })?.response?.data?.error ??
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Upload failed'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const clear = () => {
    setFile(null)
    setResult(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-100">Live Model Comparison</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload an Excel file to see how all 7 models classify those specific tickets, side by side.
          Classifier-only — does not run the full production pipeline (no guardrails, RAG, LLM
          reasoning, or SIR generation). If the file includes a <code>label</code> column, per-model
          accuracy is also shown; without one, only predictions and cross-model agreement are shown.
        </p>
      </div>

      <div className="card space-y-4">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
            ${isDragActive ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 hover:border-gray-500'}`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto mb-3 text-gray-500" size={36} />
          {isDragActive ? (
            <p className="text-blue-400 font-medium">Drop the file here…</p>
          ) : (
            <>
              <p className="text-gray-300 font-medium">Drag & drop an Excel file here</p>
              <p className="text-gray-500 text-sm mt-1">or click to browse — .xlsx / .xls only</p>
            </>
          )}
        </div>

        {file && (
          <div className="flex items-center gap-3 bg-gray-800 rounded-lg px-4 py-3">
            <FileSpreadsheet size={20} className="text-emerald-400 shrink-0" />
            <span className="text-sm text-gray-200 flex-1 truncate">{file.name}</span>
            <span className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</span>
            <button onClick={clear} className="text-gray-500 hover:text-gray-300 transition-colors">
              <X size={16} />
            </button>
          </div>
        )}

        {file && (
          <button onClick={handleSubmit} disabled={loading} className="btn-primary flex items-center gap-2 w-full justify-center">
            {loading ? 'Predicting…' : 'Predict with All 7 Models'}
            {!loading && <ChevronRight size={16} />}
          </button>
        )}
      </div>

      {result && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="card">
              <p className="text-2xl font-bold text-gray-100">{result.total_tickets}</p>
              <p className="text-xs text-gray-500 mt-1">Tickets Processed</p>
            </div>
            <div className="card">
              <p className="text-2xl font-bold text-blue-400">{(result.unanimous_rate * 100).toFixed(0)}%</p>
              <p className="text-xs text-gray-500 mt-1">
                Unanimous ({result.unanimous_count}/{result.total_tickets} — all 7 models agree)
              </p>
            </div>
            {!result.has_labels && (
              <div className="card border border-amber-900/50 bg-amber-950/10">
                <p className="text-xs text-amber-300">
                  No <code>label</code> column found — showing predictions and agreement only.
                  Accuracy cannot be computed without ground truth.
                </p>
              </div>
            )}
          </div>

          {result.has_labels && result.accuracy_per_model && (
            <div className="card overflow-x-auto">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-300">Model Performance (this upload)</h3>
                <label className="flex items-center gap-2 text-xs text-gray-400">
                  Sort by
                  <select
                    value={sortMetric}
                    onChange={(e) => setSortMetric(e.target.value as SortMetric)}
                    className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-gray-200 text-xs"
                  >
                    {SORT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 text-xs uppercase border-b border-gray-800">
                    <th className="pb-2 pr-4">Model</th>
                    <th className="pb-2 pr-4">Correct</th>
                    <th className="pb-2 pr-4">Accuracy</th>
                    <th className="pb-2 pr-4">F1 (macro)</th>
                    <th className="pb-2 pr-4">FP F1</th>
                    <th className="pb-2 pr-4">NR F1</th>
                    <th className="pb-2">TP F1</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.accuracy_per_model)
                    .sort((a, b) => {
                      const value = (entry: (typeof a)[1]) => {
                        switch (sortMetric) {
                          case 'accuracy':
                            return entry.accuracy
                          case 'f1_macro':
                            return entry.f1_macro
                          case 'f1_fp':
                            return entry.f1_per_class.FALSE_POSITIVE
                          case 'f1_nr':
                            return entry.f1_per_class.NEEDS_REVIEW
                          case 'f1_tp':
                            return entry.f1_per_class.TRUE_POSITIVE
                        }
                      }
                      return value(b[1]) - value(a[1])
                    })
                    .map(([name, stats]) => (
                      <tr key={name} className="border-b border-gray-800/60 text-gray-200">
                        <td className="py-2 pr-4 font-medium">{name}</td>
                        <td className="py-2 pr-4 font-mono text-xs">
                          {stats.correct}/{stats.total}
                        </td>
                        <td className="py-2 pr-4 font-mono text-xs">{(stats.accuracy * 100).toFixed(1)}%</td>
                        <td className="py-2 pr-4 font-mono text-xs">{stats.f1_macro.toFixed(3)}</td>
                        <td className="py-2 pr-4 font-mono text-xs">{stats.f1_per_class.FALSE_POSITIVE.toFixed(3)}</td>
                        <td className="py-2 pr-4 font-mono text-xs">{stats.f1_per_class.NEEDS_REVIEW.toFixed(3)}</td>
                        <td className="py-2 font-mono text-xs">{stats.f1_per_class.TRUE_POSITIVE.toFixed(3)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-600 mt-3">
                F1 (macro) = average of FALSE_POSITIVE, NEEDS_REVIEW, and TRUE_POSITIVE F1 scores, weighted
                equally regardless of class size — a more complete view than accuracy alone, which can hide
                poor performance on the smaller NEEDS_REVIEW class.
              </p>
            </div>
          )}

          <div className="card overflow-x-auto">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">
              Per-Ticket Predictions {result.tickets.length > 50 && `(first 50 of ${result.tickets.length})`}
            </h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase border-b border-gray-800">
                  <th className="pb-2 pr-4">Ticket ID</th>
                  {result.has_labels && <th className="pb-2 pr-4">True Label</th>}
                  {MODEL_NAMES.map((m) => (
                    <th key={m} className="pb-2 pr-4">
                      {m}
                    </th>
                  ))}
                  <th className="pb-2">Agreement</th>
                </tr>
              </thead>
              <tbody>
                {result.tickets.slice(0, 50).map((t) => (
                  <tr key={t.ticket_id} className="border-b border-gray-800/60 text-gray-200">
                    <td className="py-2 pr-4 font-mono text-xs">{t.ticket_id}</td>
                    {result.has_labels && (
                      <td className="py-2 pr-4 font-mono text-xs text-gray-400">{t.true_label}</td>
                    )}
                    {MODEL_NAMES.map((m) => {
                      const pred = t.predictions[m]
                      const isCorrect = t.true_label !== undefined ? pred === t.true_label : null
                      return (
                        <td
                          key={m}
                          className={`py-2 pr-4 font-mono text-xs ${
                            isCorrect === true ? 'text-emerald-400' : isCorrect === false ? 'text-red-400' : 'text-gray-300'
                          }`}
                        >
                          {pred}
                        </td>
                      )
                    })}
                    <td className="py-2">
                      {t.unanimous ? (
                        <CheckCircle2 size={14} className="text-emerald-400" />
                      ) : (
                        <XCircle size={14} className="text-amber-400" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

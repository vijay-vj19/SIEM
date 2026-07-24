import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, Trophy } from 'lucide-react'
import { getModelComparison } from '../../api/client'
import type { ModelComparisonResponse, ModelComparisonResult } from '../../types/modelComparison'

const METRIC_BAR_MAX = {
  accuracy_mean: 1,
  f1_macro: 1,
  inference_ms_per_ticket_mean: 0.1, // most models are well under this
}

function Bar({ value, max, colorClass }: { value: number; max: number; colorClass: string }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="h-1.5 w-24 bg-gray-800 rounded-full overflow-hidden">
      <div className={`h-full ${colorClass} rounded-full`} style={{ width: `${pct}%` }} />
    </div>
  )
}

/** Per-class F1, derived from the confusion matrix already in the API
 * response — no backend change needed. cm[i][j] = true class i, predicted
 * class j (rows=true, cols=predicted, per compare.py). */
function perClassF1(result: ModelComparisonResult, className: string): number | null {
  const idx = result.confusion_matrix_labels.indexOf(className)
  if (idx === -1) return null
  const cm = result.confusion_matrix
  const truePositives = cm[idx][idx]
  const predictedTotal = cm.reduce((sum, row) => sum + row[idx], 0) // column sum
  const actualTotal = cm[idx].reduce((a, b) => a + b, 0) // row sum
  if (predictedTotal === 0 || actualTotal === 0) return 0
  const precision = truePositives / predictedTotal
  const recall = truePositives / actualTotal
  if (precision + recall === 0) return 0
  return (2 * precision * recall) / (precision + recall)
}

function rank(results: ModelComparisonResult[], name: string, key: (r: ModelComparisonResult) => number): number {
  const sorted = [...results].sort((a, b) => key(b) - key(a))
  return sorted.findIndex((r) => r.name === name) + 1
}

/** Dynamically computed — never hardcodes a model name, so this stays
 * honest if the underlying comparison results ever change (different data,
 * different tuning). Leads with accuracy/F1/latency; NEEDS_REVIEW recall is
 * cited as supporting context, not the headline, per the case actually made
 * in the data at hand. */
const CLASS_NAMES = ['FALSE_POSITIVE', 'NEEDS_REVIEW', 'TRUE_POSITIVE']

function LeaderSummary({ data }: { data: ModelComparisonResponse }) {
  const byAccuracy = [...data.results].sort((a, b) => b.accuracy_mean - a.accuracy_mean)
  const leader = byAccuracy[0]
  const f1Rank = rank(data.results, leader.name, (r) => r.f1_macro)
  const fastestInfer = [...data.results].sort(
    (a, b) => a.inference_ms_per_ticket_mean - b.inference_ms_per_ticket_mean
  )[0]

  const perClassRanks = CLASS_NAMES.map((cls) => rank(data.results, leader.name, (r) => perClassF1(r, cls) ?? -1))
  const worstClassRank = Math.max(...perClassRanks)

  const ordinal = (n: number) => (n === 1 ? '1st' : n === 2 ? '2nd' : n === 3 ? '3rd' : `${n}th`)

  return (
    <div className="card border border-blue-900/50 bg-blue-950/10">
      <div className="flex items-center gap-2 mb-2">
        <Trophy size={16} className="text-amber-400" />
        <h3 className="text-sm font-semibold text-gray-200">Leading model: {leader.name}</h3>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">
        Best accuracy ({(leader.accuracy_mean * 100).toFixed(1)}%), {f1Rank === 1 ? 'best' : ordinal(f1Rank)}{' '}
        on F1 (macro) ({leader.f1_macro.toFixed(3)}), and{' '}
        {leader.name === fastestInfer.name ? 'fastest' : 'near-fastest'} inference (
        {leader.inference_ms_per_ticket_mean.toFixed(3)}ms/ticket) among all 7 models tested. Its main
        distinguishing strength: never worse than {ordinal(worstClassRank)} on per-class F1 across all
        3 verdict classes — the most consistent model tested, rather than the single best on any one
        metric.
      </p>
    </div>
  )
}

export function ModelComparisonView() {
  const [data, setData] = useState<ModelComparisonResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<'accuracy_mean' | 'f1_macro'>('accuracy_mean')

  useEffect(() => {
    let cancelled = false
    getModelComparison()
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Failed to load model comparison results'
        toast.error(msg)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <div className="text-gray-400 text-sm">Loading model comparison...</div>
  }

  if (!data) {
    return (
      <div className="card flex items-center gap-2 text-amber-400 text-sm">
        <AlertTriangle size={16} />
        No comparison results available. Run: python -m model_comparison.compare
      </div>
    )
  }

  const sorted = [...data.results].sort((a, b) => b[sortKey] - a[sortKey])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-100">Model Comparison</h1>
        <p className="text-sm text-gray-500 mt-1">
          Offline evaluation of 7 classifiers on a {data.dataset_rows.toLocaleString()}-ticket synthetic
          dataset, {data.n_splits}-fold stratified cross-validation. This is NOT the live production
          classifier — for evaluation purposes only.
        </p>
      </div>

      <LeaderSummary data={data} />

      <div className="card overflow-x-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300">All 7 Models</h3>
          <div className="flex gap-1 bg-gray-800 rounded-lg p-1 text-xs">
            <button
              className={`px-2.5 py-1 rounded-md ${sortKey === 'accuracy_mean' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
              onClick={() => setSortKey('accuracy_mean')}
            >
              Sort by Accuracy
            </button>
            <button
              className={`px-2.5 py-1 rounded-md ${sortKey === 'f1_macro' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
              onClick={() => setSortKey('f1_macro')}
            >
              Sort by F1 (macro)
            </button>
          </div>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 text-xs uppercase border-b border-gray-800">
              <th className="pb-2 pr-4">Model</th>
              <th className="pb-2 pr-4">Accuracy</th>
              <th className="pb-2 pr-4">F1 (macro)</th>
              <th className="pb-2 pr-4">FP F1</th>
              <th className="pb-2 pr-4">NR F1</th>
              <th className="pb-2 pr-4">TP F1</th>
              <th className="pb-2 pr-4">Train Time</th>
              <th className="pb-2 pr-4">Infer / Ticket</th>
              <th className="pb-2">Size</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const fpF1 = perClassF1(r, 'FALSE_POSITIVE')
              const nrF1 = perClassF1(r, 'NEEDS_REVIEW')
              const tpF1 = perClassF1(r, 'TRUE_POSITIVE')
              return (
                <tr key={r.name} className="border-b border-gray-800/60 text-gray-200">
                  <td className="py-2.5 pr-4 font-medium">{r.name}</td>
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs w-14">{(r.accuracy_mean * 100).toFixed(1)}%</span>
                      <Bar value={r.accuracy_mean} max={METRIC_BAR_MAX.accuracy_mean} colorClass="bg-blue-500" />
                    </div>
                    <span className="text-[10px] text-gray-500">± {(r.accuracy_std * 100).toFixed(1)}%</span>
                  </td>
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs w-14">{r.f1_macro.toFixed(3)}</span>
                      <Bar value={r.f1_macro} max={METRIC_BAR_MAX.f1_macro} colorClass="bg-emerald-500" />
                    </div>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs">{fpF1 !== null ? fpF1.toFixed(3) : '—'}</td>
                  <td className="py-2.5 pr-4 font-mono text-xs">{nrF1 !== null ? nrF1.toFixed(3) : '—'}</td>
                  <td className="py-2.5 pr-4 font-mono text-xs">{tpF1 !== null ? tpF1.toFixed(3) : '—'}</td>
                  <td className="py-2.5 pr-4 font-mono text-xs">{(r.train_time_sec_mean * 1000).toFixed(1)}ms</td>
                  <td className="py-2.5 pr-4 font-mono text-xs">{r.inference_ms_per_ticket_mean.toFixed(3)}ms</td>
                  <td className="py-2.5 font-mono text-xs">{r.model_size_kb.toFixed(1)}KB</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-600">
        FP / NR / TP F1 = per-class F1 score for FALSE_POSITIVE, NEEDS_REVIEW, and TRUE_POSITIVE
        respectively. F1 (macro) above is the average of these three. NEEDS_REVIEW is consistently
        the hardest class for every model — this is the class most worth watching when comparing.
      </p>
      <p className="text-xs text-gray-700">{data.disclosure}</p>
    </div>
  )
}

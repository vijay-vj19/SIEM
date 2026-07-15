import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle } from 'lucide-react'
import { getLangsmithRuns, getLangsmithSummary } from '../../api/client'
import { StatTile } from '../charts/StatTile'
import { DonutChart } from '../charts/DonutChart'
import { TrendChart } from './TrendChart'
import { RunsTable } from './RunsTable'
import type { LangSmithRange, LangSmithRun, LangSmithSummary } from '../../types/langsmith'

const RANGES: { key: LangSmithRange; label: string }[] = [
  { key: '24h', label: '24h' },
  { key: '7d', label: '7d' },
  { key: '30d', label: '30d' },
]

export function LlmPerformanceView() {
  const [range, setRange] = useState<LangSmithRange>('24h')
  const [summary, setSummary] = useState<LangSmithSummary | null>(null)
  const [runs, setRuns] = useState<LangSmithRun[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    Promise.all([getLangsmithSummary(range), getLangsmithRuns(range, 50)])
      .then(([summaryRes, runsRes]) => {
        if (cancelled) return
        setSummary(summaryRes)
        setRuns(runsRes.runs)
        if (summaryRes.error) toast.error(`LangSmith: ${summaryRes.error}`)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to load LangSmith data'
        toast.error(msg)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [range])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">LLM Performance</h1>
          <p className="text-xs text-gray-500 mt-1">
            Live GPT-4o-mini call stats, traced via LangSmith.
          </p>
        </div>
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                range === r.key ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {loading && !summary && <p className="text-sm text-gray-500">Loading…</p>}

      {!loading && summary && !summary.configured && (
        <div className="card border border-amber-500/30 bg-amber-500/[0.03] flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-400">LangSmith not configured</p>
            <p className="text-xs text-gray-400 mt-1">
              Set <code className="text-gray-300">LANGSMITH_API_KEY</code>,{' '}
              <code className="text-gray-300">LANGSMITH_TRACING=true</code>, and{' '}
              <code className="text-gray-300">LANGSMITH_PROJECT</code> in{' '}
              <code className="text-gray-300">backend/.env</code>, then restart the backend.
            </p>
          </div>
        </div>
      )}

      {summary && summary.configured && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatTile
              value={summary.total_runs.toLocaleString()}
              label="Total Runs"
              sublabel={`in last ${range}`}
              valueClass="text-blue-400"
              borderClass="border-blue-500/30"
            />
            <StatTile
              value={`${(summary.error_rate * 100).toFixed(1)}%`}
              label="Error Rate"
              sublabel={`${summary.error_count} of ${summary.total_runs} failed`}
              valueClass={summary.error_count > 0 ? 'text-red-400' : 'text-emerald-400'}
              borderClass={summary.error_count > 0 ? 'border-red-500/30' : 'border-emerald-500/30'}
            />
            <StatTile
              value={`${summary.p95_latency_ms.toLocaleString()} ms`}
              label="P95 Latency"
              sublabel={`avg ${summary.avg_latency_ms.toLocaleString()} ms · p50 ${summary.p50_latency_ms.toLocaleString()} ms`}
              valueClass="text-amber-400"
              borderClass="border-amber-500/30"
            />
            <StatTile
              value={`$${summary.estimated_cost_usd.toFixed(4)}`}
              label="Estimated Cost"
              sublabel={`${summary.total_tokens.toLocaleString()} tokens`}
              valueClass="text-purple-400"
              borderClass="border-purple-500/30"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <TrendChart buckets={summary.runs_over_time} range={range} />
            </div>
            <DonutChart
              title="Token Usage"
              centerValue={summary.total_tokens.toLocaleString()}
              centerLabel="total tokens"
              segments={[
                { label: 'Prompt Tokens', value: summary.prompt_tokens, colorClass: 'text-blue-400' },
                { label: 'Completion Tokens', value: summary.completion_tokens, colorClass: 'text-purple-400' },
              ]}
            />
          </div>

          <RunsTable runs={runs} />
        </>
      )}
    </div>
  )
}

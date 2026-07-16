import { useState } from 'react'
import type { LangSmithRange, RunsOverTimeBucket } from '../../types/langsmith'
import { DASHBOARD_TIMEZONE, dashboardTzAbbreviation } from '../../lib/timezone'

interface Props {
  buckets: RunsOverTimeBucket[]
  range: LangSmithRange
}

const CHART_HEIGHT = 130
const MAX_DIRECT_LABELS = 14 // beyond this, per-bar count labels get too crowded — rely on gridlines + hover instead
const MAX_X_LABELS = 8 // thin out x-axis labels so they don't overlap on wide ranges (e.g. 30d)

function formatBucketLabel(bucket: string, range: LangSmithRange): string {
  const d = new Date(bucket)
  if (range === '24h') {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: DASHBOARD_TIMEZONE })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', timeZone: DASHBOARD_TIMEZONE })
}

function niceMax(value: number): number {
  if (value <= 4) return Math.max(value, 1)
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)))
  const normalized = value / magnitude
  const niceNormalized = normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return niceNormalized * magnitude
}

export function TrendChart({ buckets, range }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)

  if (buckets.length === 0) {
    return (
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">
          Runs Over Time <span className="text-gray-500 font-normal">({dashboardTzAbbreviation()})</span>
        </h3>
        <p className="text-xs text-gray-500 py-8 text-center">No runs in this window.</p>
      </div>
    )
  }

  const rawMax = Math.max(...buckets.map((b) => b.count))
  const max = niceMax(rawMax)
  const ticks = [max, Math.round(max / 2), 0]
  const showDirectLabels = buckets.length <= MAX_DIRECT_LABELS
  const labelStride = Math.max(1, Math.ceil(buckets.length / MAX_X_LABELS))

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">
        Runs Over Time <span className="text-gray-500 font-normal">({dashboardTzAbbreviation()})</span>
      </h3>

      <div className="flex gap-3">
        {/* Y-axis ticks */}
        <div
          className="flex flex-col justify-between text-[10px] text-gray-500 font-mono shrink-0 w-7 text-right"
          style={{ height: CHART_HEIGHT }}
        >
          {ticks.map((t, i) => (
            <span key={i}>{t}</span>
          ))}
        </div>

        {/* Chart area */}
        <div className="relative flex-1 min-w-0">
          {/* Gridlines */}
          <div className="absolute inset-0 flex flex-col justify-between" style={{ height: CHART_HEIGHT }}>
            {ticks.map((_, i) => (
              <div key={i} className="border-t border-gray-800" />
            ))}
          </div>

          {/* Bars */}
          <div className="relative flex items-end gap-1" style={{ height: CHART_HEIGHT }}>
            {buckets.map((b, i) => {
              const isHovered = hovered === i
              const height = max > 0 ? Math.max((b.count / max) * CHART_HEIGHT, b.count > 0 ? 4 : 0) : 0
              return (
                <div
                  key={b.bucket}
                  className="relative flex-1 flex flex-col items-center justify-end h-full cursor-pointer group"
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                >
                  {isHovered && (
                    <div className="absolute -top-9 z-10 whitespace-nowrap rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-gray-100 shadow-lg pointer-events-none">
                      <span className="font-semibold">{b.count}</span> run{b.count === 1 ? '' : 's'} ·{' '}
                      {formatBucketLabel(b.bucket, range)}
                    </div>
                  )}
                  {showDirectLabels && !isHovered && b.count > 0 && (
                    <span className="text-[10px] font-mono text-gray-500 mb-1">{b.count}</span>
                  )}
                  <div
                    className="w-full max-w-[28px] mx-auto rounded-t-sm bg-blue-500 transition-all duration-150 origin-bottom"
                    style={{
                      height,
                      transform: isHovered ? 'scaleX(1.25)' : 'scaleX(1)',
                      filter: isHovered ? 'brightness(1.3)' : 'none',
                    }}
                  />
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* X-axis labels */}
      <div className="flex gap-1 mt-2 pl-[calc(1.75rem+0.75rem)]">
        {buckets.map((b, i) => (
          <span
            key={b.bucket}
            className={`flex-1 text-center text-[10px] font-mono truncate transition-colors duration-150 ${
              hovered === i ? 'text-gray-200' : 'text-gray-600'
            }`}
          >
            {i % labelStride === 0 ? formatBucketLabel(b.bucket, range) : ''}
          </span>
        ))}
      </div>
    </div>
  )
}

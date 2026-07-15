import { useState } from 'react'
import type { LangSmithRange, RunsOverTimeBucket } from '../../types/langsmith'

interface Props {
  buckets: RunsOverTimeBucket[]
  range: LangSmithRange
}

const CHART_HEIGHT = 110

function formatBucketLabel(bucket: string, range: LangSmithRange): string {
  const d = new Date(bucket)
  if (range === '24h') {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export function TrendChart({ buckets, range }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)

  if (buckets.length === 0) {
    return (
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Runs Over Time</h3>
        <p className="text-xs text-gray-500 py-8 text-center">No runs in this window.</p>
      </div>
    )
  }

  const max = Math.max(...buckets.map((b) => b.count), 1)

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Runs Over Time</h3>
      <div className="flex items-end gap-1.5" style={{ height: CHART_HEIGHT }}>
        {buckets.map((b, i) => {
          const isHovered = hovered === i
          const height = Math.max((b.count / max) * CHART_HEIGHT, 3)
          return (
            <div
              key={b.bucket}
              className="relative flex-1 flex flex-col items-center justify-end h-full cursor-pointer"
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {isHovered && (
                <div className="absolute -top-9 z-10 whitespace-nowrap rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-gray-100 shadow-lg pointer-events-none">
                  <span className="font-semibold">{b.count}</span> run{b.count === 1 ? '' : 's'} ·{' '}
                  {formatBucketLabel(b.bucket, range)}
                </div>
              )}
              <div
                className="w-full rounded-t-sm bg-blue-500 transition-all duration-150 origin-bottom"
                style={{
                  height,
                  transform: isHovered ? 'scaleX(1.2)' : 'scaleX(1)',
                  filter: isHovered ? 'brightness(1.3)' : 'none',
                }}
              />
            </div>
          )
        })}
      </div>
      <div className="flex gap-1.5 mt-1.5">
        {buckets.map((b, i) => (
          <span
            key={b.bucket}
            className={`flex-1 text-center text-[9px] font-mono truncate transition-colors duration-150 ${
              hovered === i ? 'text-gray-200' : 'text-gray-600'
            }`}
          >
            {formatBucketLabel(b.bucket, range)}
          </span>
        ))}
      </div>
    </div>
  )
}

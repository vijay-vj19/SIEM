import { useState } from 'react'
import { ArrowRight } from 'lucide-react'

interface Props {
  kbHitRate: number
  kbHitCount: number
  kbHitTotal: number
  kbMissRate: number
  kbMissCount: number
  kbMissTotal: number
}

const CHART_HEIGHT = 130
const SCALE_MAX = 20 // %, fits both example rates with headroom
const TICKS = [0, 10, 20]

export function FPRateChart({
  kbHitRate,
  kbHitCount,
  kbHitTotal,
  kbMissRate,
  kbMissCount,
  kbMissTotal,
}: Props) {
  const [hovered, setHovered] = useState<'hit' | 'miss' | null>(null)
  const hitHeight = (kbHitRate / SCALE_MAX) * CHART_HEIGHT
  const missHeight = (kbMissRate / SCALE_MAX) * CHART_HEIGHT
  const multiplier = (kbMissRate / kbHitRate).toFixed(1)

  const bars = [
    {
      key: 'hit' as const,
      rate: kbHitRate,
      count: kbHitCount,
      total: kbHitTotal,
      height: hitHeight,
      colorClass: 'bg-blue-400',
      label: 'KB Hit',
      sublabel: '(similar case found)',
    },
    {
      key: 'miss' as const,
      rate: kbMissRate,
      count: kbMissCount,
      total: kbMissTotal,
      height: missHeight,
      colorClass: 'bg-blue-700',
      label: 'KB Miss',
      sublabel: '(LLM reasons alone)',
    },
  ]

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-gray-300">False-Positive Rate by KB Availability</h3>
        <span className="flex items-center gap-1.5 text-xs text-amber-400 font-semibold whitespace-nowrap shrink-0">
          ~{multiplier}x higher FP rate without KB grounding
          <ArrowRight size={14} />
        </span>
      </div>
      <p className="text-[11px] text-gray-500 mb-4">fresh / cache-miss tickets</p>

      <div className="flex gap-4">
        <div className="flex flex-col justify-between text-[10px] text-gray-500 font-mono py-0.5" style={{ height: CHART_HEIGHT }}>
          {[...TICKS].reverse().map((t) => (
            <span key={t}>{t}%</span>
          ))}
        </div>

        <div className="flex-1 flex items-end justify-around border-l border-b border-gray-800 pl-4">
          {bars.map((b) => {
            const isHovered = hovered === b.key
            return (
              <div key={b.key} className="relative flex flex-col items-center gap-2">
                {isHovered && (
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-full z-10 whitespace-nowrap rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-gray-100 shadow-lg pointer-events-none">
                    <span className="font-semibold">{b.label}</span> FP rate: {b.rate}%
                    <br />
                    <span className="text-gray-400">{b.count} of {b.total.toLocaleString()} tickets</span>
                  </div>
                )}
                <span className={`text-sm font-mono transition-colors duration-150 ${isHovered ? 'text-gray-100' : 'text-gray-200'}`}>
                  {b.rate}% <span className="text-gray-500">({b.count} of {b.total.toLocaleString()})</span>
                </span>
                <div
                  className={`w-16 rounded-t-md cursor-pointer transition-all duration-150 origin-bottom ${b.colorClass}`}
                  style={{
                    height: b.height,
                    transform: isHovered ? 'scale(1.12)' : 'scale(1)',
                    filter: isHovered ? 'brightness(1.3)' : 'none',
                  }}
                  onMouseEnter={() => setHovered(b.key)}
                  onMouseLeave={() => setHovered(null)}
                />
                <span className={`text-xs text-center transition-colors duration-150 ${isHovered ? 'text-gray-200' : 'text-gray-400'}`}>
                  {b.label}
                  <br />
                  <span className="text-[10px] text-gray-500">{b.sublabel}</span>
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

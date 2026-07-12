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
  const hitHeight = (kbHitRate / SCALE_MAX) * CHART_HEIGHT
  const missHeight = (kbMissRate / SCALE_MAX) * CHART_HEIGHT
  const multiplier = (kbMissRate / kbHitRate).toFixed(1)

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300">False-Positive Rate by KB Availability</h3>
      <p className="text-[11px] text-gray-500 mb-4">fresh / cache-miss tickets</p>

      <div className="flex items-center justify-center gap-2 text-xs text-amber-400 mb-4">
        <span className="font-semibold">~{multiplier}x higher FP rate without KB grounding</span>
        <ArrowRight size={14} />
      </div>

      <div className="flex gap-4">
        <div className="flex flex-col justify-between text-[10px] text-gray-500 font-mono py-0.5" style={{ height: CHART_HEIGHT }}>
          {[...TICKS].reverse().map((t) => (
            <span key={t}>{t}%</span>
          ))}
        </div>

        <div className="flex-1 flex items-end justify-around border-l border-b border-gray-800 pl-4">
          <div className="flex flex-col items-center gap-2">
            <span className="text-sm font-mono text-gray-200">
              {kbHitRate}% <span className="text-gray-500">({kbHitCount} of {kbHitTotal})</span>
            </span>
            <div
              className="w-16 rounded-t-md bg-blue-400"
              style={{ height: hitHeight }}
              title={`KB Hit: ${kbHitRate}% (${kbHitCount} of ${kbHitTotal})`}
            />
            <span className="text-xs text-gray-400 text-center">
              KB Hit
              <br />
              <span className="text-[10px] text-gray-500">(similar case found)</span>
            </span>
          </div>

          <div className="flex flex-col items-center gap-2">
            <span className="text-sm font-mono text-gray-200">
              {kbMissRate}% <span className="text-gray-500">({kbMissCount} of {kbMissTotal})</span>
            </span>
            <div
              className="w-16 rounded-t-md bg-blue-700"
              style={{ height: missHeight }}
              title={`KB Miss: ${kbMissRate}% (${kbMissCount} of ${kbMissTotal})`}
            />
            <span className="text-xs text-gray-400 text-center">
              KB Miss
              <br />
              <span className="text-[10px] text-gray-500">(LLM reasons alone)</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'

interface Segment {
  label: string
  value: number
  colorClass: string // tailwind text-* class, used as SVG stroke via currentColor
}

interface Props {
  title: string
  segments: Segment[]
  centerValue: string
  centerLabel: string
}

const SIZE = 160
const STROKE_WIDTH = 18
const STROKE_WIDTH_HOVER = 24
const RADIUS = (SIZE - STROKE_WIDTH_HOVER) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const GAP = 3 // px arc-length gap between segments

export function DonutChart({ title, segments, centerValue, centerLabel }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)
  const total = segments.reduce((sum, s) => sum + s.value, 0)
  let cumulative = 0

  const active = hovered !== null ? segments[hovered] : null
  const activePct = active && total > 0 ? (active.value / total) * 100 : 0

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">{title}</h3>
      <div className="flex flex-col items-center gap-4">
        <div className="relative" style={{ width: SIZE, height: SIZE }}>
          <svg width={SIZE} height={SIZE} className="-rotate-90 overflow-visible">
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              strokeWidth={STROKE_WIDTH}
              className="stroke-gray-800"
            />
            {segments.map((s, i) => {
              const fraction = total > 0 ? s.value / total : 0
              const arcLength = fraction * CIRCUMFERENCE
              const visibleLength = Math.max(arcLength - GAP, 0)
              const dashOffset = -cumulative
              cumulative += arcLength
              const isHovered = hovered === i
              const isDimmed = hovered !== null && !isHovered
              return (
                <circle
                  key={i}
                  cx={SIZE / 2}
                  cy={SIZE / 2}
                  r={RADIUS}
                  fill="none"
                  strokeWidth={isHovered ? STROKE_WIDTH_HOVER : STROKE_WIDTH}
                  strokeLinecap="round"
                  strokeDasharray={`${visibleLength} ${CIRCUMFERENCE - visibleLength}`}
                  strokeDashoffset={dashOffset}
                  opacity={isDimmed ? 0.35 : 1}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                  className={`${s.colorClass} stroke-current transition-all duration-150 cursor-pointer`}
                />
              )
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold text-gray-100">{active ? active.value.toLocaleString() : centerValue}</span>
            <span className="text-[11px] text-gray-500 text-center px-4">
              {active ? `${active.label} · ${activePct.toFixed(1)}%` : centerLabel}
            </span>
          </div>
        </div>
        <ul className="w-full space-y-1.5">
          {segments.map((s, i) => {
            const fraction = total > 0 ? s.value / total : 0
            const isHovered = hovered === i
            return (
              <li
                key={i}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className={`flex items-center justify-between text-xs rounded-md px-1.5 py-1 -mx-1.5 cursor-pointer transition-colors duration-150 ${
                  isHovered ? 'bg-gray-800' : ''
                }`}
              >
                <span className={`flex items-center gap-2 ${isHovered ? 'text-gray-100' : 'text-gray-300'}`}>
                  <span className={`w-2.5 h-2.5 rounded-sm ${s.colorClass} bg-current`} />
                  {s.label}
                </span>
                <span className={`font-mono ${isHovered ? 'text-gray-200' : 'text-gray-400'}`}>
                  {s.value.toLocaleString()} ({(fraction * 100).toFixed(1)}%)
                </span>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

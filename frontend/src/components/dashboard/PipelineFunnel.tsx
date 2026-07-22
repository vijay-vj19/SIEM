import { useState } from 'react'

interface Stage {
  label: string
  value: number
}

interface ClassifiedSegment {
  label: string
  value: number
  colorClass: string // tailwind bg-* class
}

interface Props {
  stages: Stage[]
  classifiedTotal: number
  classifiedSegments: ClassifiedSegment[]
}

function Tooltip({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute -top-9 left-1/2 -translate-x-1/2 z-10 whitespace-nowrap rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-gray-100 shadow-lg pointer-events-none">
      {children}
    </div>
  )
}

export function PipelineFunnel({ stages, classifiedTotal, classifiedSegments }: Props) {
  const max = Math.max(...stages.map((s) => s.value), classifiedTotal)
  const [hoveredStage, setHoveredStage] = useState<string | null>(null)
  const [hoveredSegment, setHoveredSegment] = useState<number | null>(null)

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wide">Pipeline Funnel</h3>
      <div className="space-y-3">
        {stages.map((s) => {
          const isHovered = hoveredStage === s.label
          return (
            <div
              key={s.label}
              className="relative flex items-center gap-3"
              onMouseEnter={() => setHoveredStage(s.label)}
              onMouseLeave={() => setHoveredStage(null)}
            >
              <span className="w-20 text-xs text-gray-400 shrink-0">{s.label}</span>
              <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-visible cursor-pointer">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-150 origin-left"
                  style={{
                    width: `${(s.value / max) * 100}%`,
                    transform: isHovered ? 'scaleY(1.35)' : 'scaleY(1)',
                    filter: isHovered ? 'brightness(1.25)' : 'none',
                  }}
                />
              </div>
              <span className="w-14 text-right text-xs font-mono text-gray-300">
                {s.value.toLocaleString()}
              </span>
              {isHovered && (
                <Tooltip>
                  <span className="font-semibold">{s.label}</span>: {s.value.toLocaleString()} (
                  {((s.value / max) * 100).toFixed(1)}% of max)
                </Tooltip>
              )}
            </div>
          )
        })}

        <div className="relative flex items-center gap-3">
          <span className="w-20 text-xs text-gray-400 shrink-0">Classified</span>
          <div className="flex-1 flex h-3" style={{ width: `${(classifiedTotal / max) * 100}%` }}>
            {classifiedSegments.map((seg, i) => {
              const isHovered = hoveredSegment === i
              return (
                <div
                  key={seg.label}
                  className={`relative h-full transition-transform duration-150 cursor-pointer ${seg.colorClass} ${
                    i === 0 ? 'rounded-l-full' : ''
                  } ${i === classifiedSegments.length - 1 ? 'rounded-r-full' : ''}`}
                  style={{
                    width: `${(seg.value / classifiedTotal) * 100}%`,
                    marginRight: i < classifiedSegments.length - 1 ? 2 : 0,
                    transform: isHovered ? 'scaleY(1.5)' : 'scaleY(1)',
                    filter: isHovered ? 'brightness(1.25)' : 'none',
                  }}
                  onMouseEnter={() => setHoveredSegment(i)}
                  onMouseLeave={() => setHoveredSegment(null)}
                >
                  {isHovered && (
                    <Tooltip>
                      <span className="font-semibold">{seg.label}</span>: {seg.value.toLocaleString()} (
                      {((seg.value / classifiedTotal) * 100).toFixed(1)}% of classified)
                    </Tooltip>
                  )}
                </div>
              )
            })}
          </div>
          <span className="w-14 text-right text-xs font-mono text-gray-300">
            {classifiedTotal.toLocaleString()}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-gray-800">
        {classifiedSegments.map((seg, i) => (
          <span
            key={seg.label}
            onMouseEnter={() => setHoveredSegment(i)}
            onMouseLeave={() => setHoveredSegment(null)}
            className={`flex items-center gap-1.5 text-[11px] cursor-pointer transition-colors duration-150 ${
              hoveredSegment === i ? 'text-gray-100' : 'text-gray-400'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${seg.colorClass}`} />
            {seg.label} {seg.value.toLocaleString()}
          </span>
        ))}
      </div>
    </div>
  )
}

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

export function PipelineFunnel({ stages, classifiedTotal, classifiedSegments }: Props) {
  const max = Math.max(...stages.map((s) => s.value), classifiedTotal)

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Pipeline Funnel</h3>
      <div className="space-y-3">
        {stages.map((s) => (
          <div key={s.label} className="flex items-center gap-3">
            <span className="w-20 text-xs text-gray-400 shrink-0">{s.label}</span>
            <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{ width: `${(s.value / max) * 100}%` }}
                title={`${s.label}: ${s.value.toLocaleString()}`}
              />
            </div>
            <span className="w-14 text-right text-xs font-mono text-gray-300">
              {s.value.toLocaleString()}
            </span>
          </div>
        ))}

        <div className="flex items-center gap-3">
          <span className="w-20 text-xs text-gray-400 shrink-0">Classified</span>
          <div className="flex-1 flex h-3" style={{ width: `${(classifiedTotal / max) * 100}%` }}>
            {classifiedSegments.map((seg, i) => (
              <div
                key={seg.label}
                className={`h-full ${seg.colorClass} ${i === 0 ? 'rounded-l-full' : ''} ${
                  i === classifiedSegments.length - 1 ? 'rounded-r-full' : ''
                }`}
                style={{
                  width: `${(seg.value / classifiedTotal) * 100}%`,
                  marginRight: i < classifiedSegments.length - 1 ? 2 : 0,
                }}
                title={`${seg.label}: ${seg.value.toLocaleString()}`}
              />
            ))}
          </div>
          <span className="w-14 text-right text-xs font-mono text-gray-300">
            {classifiedTotal.toLocaleString()}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-gray-800">
        {classifiedSegments.map((seg) => (
          <span key={seg.label} className="flex items-center gap-1.5 text-[11px] text-gray-400">
            <span className={`w-2 h-2 rounded-full ${seg.colorClass}`} />
            {seg.label} {seg.value.toLocaleString()}
          </span>
        ))}
      </div>
    </div>
  )
}

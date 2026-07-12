interface Props {
  notes: string[]
}

export function KpiNotes({ notes }: Props) {
  return (
    <div className="card border border-amber-500/20 bg-amber-500/[0.03]">
      <h3 className="text-sm font-semibold text-amber-400 mb-3">KPI Notes</h3>
      <ul className="space-y-2">
        {notes.map((note, i) => (
          <li key={i} className="flex gap-2 text-xs text-gray-300">
            <span className="text-amber-500 shrink-0">•</span>
            {note}
          </li>
        ))}
      </ul>
    </div>
  )
}

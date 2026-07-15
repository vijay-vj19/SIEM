interface Props {
  value: string
  label: string
  sublabel: string
  valueClass: string
  borderClass: string
}

export function StatTile({ value, label, sublabel, valueClass, borderClass }: Props) {
  return (
    <div className={`card border ${borderClass}`}>
      <p className={`text-3xl font-bold ${valueClass}`}>{value}</p>
      <p className="text-sm font-semibold text-gray-200 mt-1">{label}</p>
      <p className="text-xs text-gray-500 mt-0.5">{sublabel}</p>
    </div>
  )
}

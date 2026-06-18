import type { TriageResult } from '../types/ticket'

type Verdict = TriageResult['verdict']

const CONFIG: Record<Verdict, { label: string; classes: string }> = {
  TRUE_POSITIVE: {
    label: 'TRUE POSITIVE',
    classes: 'bg-red-500/15 text-red-400 border-red-500/30',
  },
  FALSE_POSITIVE: {
    label: 'FALSE POSITIVE',
    classes: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  },
  NEEDS_REVIEW: {
    label: 'NEEDS REVIEW',
    classes: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  },
}

interface Props {
  verdict: Verdict
  size?: 'sm' | 'md'
}

export function StatusBadge({ verdict, size = 'md' }: Props) {
  const { label, classes } = CONFIG[verdict]
  const padding = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold tracking-wider ${padding} ${classes}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {label}
    </span>
  )
}

import { FileText, ChevronUp, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { StatusBadge } from './StatusBadge'
import type { TriageResult } from '../types/ticket'

interface Props {
  results: TriageResult[]
  onSelect: (result: TriageResult) => void
  selected: TriageResult | null
}

type SortKey = 'ticket_id' | 'verdict' | 'confidence' | 'risk_score'

export function TicketTable({ results, onSelect, selected }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('ticket_id')
  const [sortAsc, setSortAsc] = useState(true)

  const sorted = [...results].sort((a, b) => {
    const av = a[sortKey] ?? ''
    const bv = b[sortKey] ?? ''
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortAsc ? cmp : -cmp
  })

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((v) => !v)
    else { setSortKey(key); setSortAsc(true) }
  }

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (
      sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />
    ) : null

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-900 text-gray-400 text-xs uppercase tracking-wider">
          <tr>
            <th
              className="px-4 py-3 text-left cursor-pointer hover:text-gray-200 select-none"
              onClick={() => toggleSort('ticket_id')}
            >
              <span className="flex items-center gap-1">Ticket ID <SortIcon k="ticket_id" /></span>
            </th>
            <th className="px-4 py-3 text-left">Rule Triggered</th>
            <th className="px-4 py-3 text-left">MITRE</th>
            <th
              className="px-4 py-3 text-left cursor-pointer hover:text-gray-200 select-none"
              onClick={() => toggleSort('verdict')}
            >
              <span className="flex items-center gap-1">Verdict <SortIcon k="verdict" /></span>
            </th>
            <th
              className="px-4 py-3 text-right cursor-pointer hover:text-gray-200 select-none"
              onClick={() => toggleSort('confidence')}
            >
              <span className="flex items-center justify-end gap-1">Confidence <SortIcon k="confidence" /></span>
            </th>
            <th
              className="px-4 py-3 text-right cursor-pointer hover:text-gray-200 select-none"
              onClick={() => toggleSort('risk_score')}
            >
              <span className="flex items-center justify-end gap-1">Risk <SortIcon k="risk_score" /></span>
            </th>
            <th className="px-4 py-3 text-center">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {sorted.map((r) => (
            <tr
              key={r.ticket_id}
              onClick={() => onSelect(r)}
              className={`transition-colors cursor-pointer ${
                selected?.ticket_id === r.ticket_id
                  ? 'bg-blue-600/10 border-l-2 border-blue-500'
                  : 'hover:bg-gray-800/50'
              }`}
            >
              <td className="px-4 py-3 font-mono text-blue-300">{r.ticket_id}</td>
              <td className="px-4 py-3 text-gray-300 max-w-[220px] truncate">{r.mitre_attack}</td>
              <td className="px-4 py-3">
                <span className="font-mono text-xs text-purple-400">{r.mitre_attack}</span>
              </td>
              <td className="px-4 py-3">
                <StatusBadge verdict={r.verdict} size="sm" />
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-300">
                {(r.confidence * 100).toFixed(0)}%
              </td>
              <td className="px-4 py-3 text-right">
                <RiskBar score={r.risk_score} />
              </td>
              <td className="px-4 py-3 text-center">
                <button
                  onClick={(e) => { e.stopPropagation(); onSelect(r) }}
                  className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                  <FileText size={13} />
                  Report
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RiskBar({ score }: { score: number }) {
  const color =
    score >= 70 ? 'bg-red-500' : score >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400 w-6 text-right">{score}</span>
    </div>
  )
}

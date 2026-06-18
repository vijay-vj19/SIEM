import { useState } from 'react'
import { Shield, Upload, FileText, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { ExcelUpload } from './components/ExcelUpload'
import { SingleTicketForm } from './components/SingleTicketForm'
import { TicketTable } from './components/TicketTable'
import { TicketDetail } from './components/TicketDetail'
import type { TriageResponse, TriageResult, TriageSummary } from './types/ticket'

type Tab = 'bulk' | 'single'

const EMPTY_SUMMARY: TriageSummary = {
  total: 0,
  true_positive: 0,
  false_positive: 0,
  needs_review: 0,
}

export default function App() {
  const [tab, setTab] = useState<Tab>('bulk')
  const [results, setResults] = useState<TriageResult[]>([])
  const [summary, setSummary] = useState<TriageSummary>(EMPTY_SUMMARY)
  const [selected, setSelected] = useState<TriageResult | null>(null)

  const handleResults = (res: TriageResponse) => {
    setResults((prev) => {
      const existingIds = new Set(prev.map((r) => r.ticket_id))
      const newResults = res.results.filter((r) => !existingIds.has(r.ticket_id))
      const merged = [...prev, ...newResults]
      // Recompute summary from merged
      setSummary({
        total: merged.length,
        true_positive: merged.filter((r) => r.verdict === 'TRUE_POSITIVE').length,
        false_positive: merged.filter((r) => r.verdict === 'FALSE_POSITIVE').length,
        needs_review: merged.filter((r) => r.verdict === 'NEEDS_REVIEW').length,
      })
      return merged
    })
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Top nav */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-3">
          <Shield size={22} className="text-blue-400" />
          <span className="font-bold text-gray-100 tracking-wide">SOC Triage AI</span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <SummaryCard
            label="Total Processed"
            value={summary.total}
            icon={<FileText size={16} className="text-blue-400" />}
            color="border-blue-500/30"
          />
          <SummaryCard
            label="True Positives"
            value={summary.true_positive}
            icon={<AlertTriangle size={16} className="text-red-400" />}
            color="border-red-500/30"
            highlight={summary.true_positive > 0 ? 'text-red-400' : undefined}
          />
          <SummaryCard
            label="False Positives"
            value={summary.false_positive}
            icon={<CheckCircle size={16} className="text-emerald-400" />}
            color="border-emerald-500/30"
          />
          <SummaryCard
            label="Needs Review"
            value={summary.needs_review}
            icon={<Clock size={16} className="text-amber-400" />}
            color="border-amber-500/30"
            highlight={summary.needs_review > 0 ? 'text-amber-400' : undefined}
          />
        </div>

        {/* Tab panel */}
        <div className="card">
          <div className="flex gap-1 mb-6 bg-gray-800 rounded-lg p-1 w-fit">
            <TabButton active={tab === 'bulk'} onClick={() => setTab('bulk')}>
              <Upload size={14} />
              Bulk Upload
            </TabButton>
            <TabButton active={tab === 'single'} onClick={() => setTab('single')}>
              <FileText size={14} />
              Single Ticket
            </TabButton>
          </div>

          {tab === 'bulk' ? (
            <ExcelUpload onResults={handleResults} />
          ) : (
            <SingleTicketForm onResults={handleResults} />
          )}
        </div>

        {/* Results table */}
        {results.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Triage Results
              </h2>
              <button
                onClick={() => { setResults([]); setSummary(EMPTY_SUMMARY); setSelected(null) }}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Clear all
              </button>
            </div>
            <TicketTable results={results} onSelect={setSelected} selected={selected} />
          </div>
        )}
      </main>

      {/* Side panel */}
      <TicketDetail result={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function SummaryCard({
  label,
  value,
  icon,
  color,
  highlight,
}: {
  label: string
  value: number
  icon: React.ReactNode
  color: string
  highlight?: string
}) {
  return (
    <div className={`card border ${color} flex items-center gap-3`}>
      <div className="p-2 bg-gray-800 rounded-lg">{icon}</div>
      <div>
        <p className="text-[11px] text-gray-500 uppercase tracking-wider">{label}</p>
        <p className={`text-2xl font-bold ${highlight ?? 'text-gray-100'}`}>{value}</p>
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors
        ${active ? 'bg-gray-700 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
    >
      {children}
    </button>
  )
}

import { X, Download, Copy, CheckCircle, Shield, Clock } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { StatusBadge } from './StatusBadge'
import type { TriageResult } from '../types/ticket'

interface Props {
  result: TriageResult | null
  onClose: () => void
}

const RAIL_COLOR: Record<string, string> = {
  PASSED: 'text-emerald-400',
  BLOCKED: 'text-red-400',
  REDACTED: 'text-amber-400',
  UNKNOWN: 'text-gray-400',
}

export function TicketDetail({ result, onClose }: Props) {
  const [copied, setCopied] = useState(false)

  if (!result) return null

  const handleDownload = () => {
    const blob = new Blob([result.sir_report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `SIR-${result.ticket_id}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2))
    setCopied(true)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  const gs = result.guardrail_status

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <aside className="relative w-full max-w-2xl bg-gray-900 border-l border-gray-800 flex flex-col h-full overflow-hidden animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 shrink-0">
          <div className="flex items-center gap-3">
            <Shield size={18} className="text-blue-400" />
            <span className="font-mono text-blue-300 font-semibold">{result.ticket_id}</span>
            <StatusBadge verdict={result.verdict} size="sm" />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleDownload} className="btn-ghost text-xs flex items-center gap-1.5">
              <Download size={13} />
              Download .md
            </button>
            <button onClick={handleCopy} className="btn-ghost text-xs flex items-center gap-1.5">
              {copied ? <CheckCircle size={13} className="text-emerald-400" /> : <Copy size={13} />}
              {copied ? 'Copied' : 'Copy JSON'}
            </button>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors ml-2">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Meta strip */}
        <div className="grid grid-cols-4 divide-x divide-gray-800 border-b border-gray-800 shrink-0">
          {[
            { label: 'Confidence', value: `${(result.confidence * 100).toFixed(0)}%` },
            { label: 'XGBoost', value: `${(result.xgboost_score * 100).toFixed(0)}%` },
            { label: 'Risk Score', value: `${result.risk_score}/100` },
            { label: 'Time', value: `${result.processing_time_ms}ms` },
          ].map(({ label, value }) => (
            <div key={label} className="px-4 py-3 text-center">
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</p>
              <p className="text-sm font-semibold text-gray-200 mt-0.5">{value}</p>
            </div>
          ))}
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* LLM Reasoning */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">LLM Reasoning</h3>
            <p className="text-sm text-gray-300 leading-relaxed bg-gray-800/50 rounded-lg p-3">
              {result.llm_reasoning}
            </p>
          </section>

          {/* Similar incidents */}
          {result.similar_past_incidents?.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Similar Past Incidents</h3>
              <div className="space-y-1.5">
                {result.similar_past_incidents.map((inc) => (
                  <div key={inc.ticket_id} className="flex items-center justify-between bg-gray-800/50 rounded-lg px-3 py-2">
                    <span className="font-mono text-xs text-blue-300">{inc.ticket_id}</span>
                    <span className="text-xs text-gray-400">{inc.verdict}</span>
                    <span className="text-xs font-mono text-gray-300">{(inc.similarity * 100).toFixed(0)}% match</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Guardrail status */}
          {gs && (
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Guardrail Status</h3>
              <div className="space-y-1.5">
                {[
                  ['Presidio PII Scan', gs.presidio_pii_scan],
                  ['NeMo Input Rail', gs.nemo_input_rail],
                  ['NeMo Output Rail', gs.nemo_output_rail],
                ].map(([label, status]) => (
                  <div key={label} className="flex items-center justify-between bg-gray-800/50 rounded-lg px-3 py-2">
                    <span className="text-xs text-gray-400">{label}</span>
                    <span className={`text-xs font-semibold ${RAIL_COLOR[status] ?? 'text-gray-400'}`}>{status}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* SIR Report */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Security Incident Report
            </h3>
            <div className="prose prose-invert prose-sm max-w-none bg-gray-800/30 rounded-xl p-4
                            prose-headings:text-gray-200 prose-p:text-gray-300 prose-code:text-blue-300
                            prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded
                            prose-table:text-xs prose-th:text-gray-400 prose-td:text-gray-300
                            prose-strong:text-gray-200 prose-pre:bg-gray-950 prose-pre:text-gray-300">
              <ReactMarkdown>{result.sir_report}</ReactMarkdown>
            </div>
          </section>
        </div>
      </aside>

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        .animate-slide-in { animation: slideIn 0.25s ease-out; }
      `}</style>
    </div>
  )
}

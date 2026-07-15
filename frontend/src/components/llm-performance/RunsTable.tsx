import { ExternalLink } from 'lucide-react'
import type { LangSmithRun } from '../../types/langsmith'

interface Props {
  runs: LangSmithRun[]
}

export function RunsTable({ runs }: Props) {
  if (runs.length === 0) {
    return (
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-300 mb-2">Recent Runs</h3>
        <p className="text-xs text-gray-500 py-6 text-center">No runs in this window.</p>
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Recent Runs</h3>
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-gray-400 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Ticket ID</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-right">Latency</th>
              <th className="px-4 py-3 text-right">Tokens</th>
              <th className="px-4 py-3 text-right">Cost</th>
              <th className="px-4 py-3 text-left">Started</th>
              <th className="px-4 py-3 text-center">Trace</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {runs.map((r) => (
              <tr key={r.run_id} className="hover:bg-gray-800/50 transition-colors">
                <td className="px-4 py-3 font-mono text-blue-300">{r.ticket_id ?? '—'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wider ${
                      r.status === 'success'
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : 'bg-red-500/15 text-red-400 border-red-500/30'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-current" />
                    {r.status.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-gray-300">{r.latency_ms.toLocaleString()} ms</td>
                <td className="px-4 py-3 text-right font-mono text-gray-300">{r.total_tokens.toLocaleString()}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-300">${r.cost_usd.toFixed(4)}</td>
                <td className="px-4 py-3 text-gray-400 text-xs">{new Date(r.started_at).toLocaleString()}</td>
                <td className="px-4 py-3 text-center">
                  {r.langsmith_url ? (
                    <a
                      href={r.langsmith_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <ExternalLink size={13} />
                      View
                    </a>
                  ) : (
                    <span className="text-xs text-gray-600">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

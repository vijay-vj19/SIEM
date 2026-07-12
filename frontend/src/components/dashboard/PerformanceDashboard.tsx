import { StatTile } from './StatTile'
import { DonutChart } from './DonutChart'
import { PipelineFunnel } from './PipelineFunnel'
import { FPRateChart } from './FPRateChart'
import { KpiNotes } from './KpiNotes'
import { MOCK_DASHBOARD_DATA } from '../../data/mockDashboard'

export function PerformanceDashboard() {
  const d = MOCK_DASHBOARD_DATA
  const processedPct = (d.processed / d.ingested) * 100
  const cacheHitPct = (d.cache.hit / d.processed) * 100
  const kbEscalated = d.kb.hit + d.kb.miss
  const kbHitPct = (d.kb.hit / kbEscalated) * 100
  const classifiedTotal =
    d.classification.truePositive + d.classification.falsePositive + d.classification.needsReview

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-100">
          Performance Dashboard — Illustrative Example ({d.ingested.toLocaleString()} tickets / day)
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Example figures for a representative daily volume — not measured production data.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          value={d.ingested.toLocaleString()}
          label="Tickets Ingested"
          sublabel="Excel · Form · API"
          valueClass="text-blue-400"
          borderClass="border-blue-500/30"
        />
        <StatTile
          value={d.processed.toLocaleString()}
          label="Tickets Processed"
          sublabel={`${processedPct.toFixed(1)}% of ingested`}
          valueClass="text-blue-400"
          borderClass="border-blue-500/30"
        />
        <StatTile
          value={`${cacheHitPct.toFixed(1)}%`}
          label="Cache Hit Rate"
          sublabel={`${d.cache.hit} of ${d.processed} · TTL ${d.cache.ttlDays}d`}
          valueClass="text-amber-400"
          borderClass="border-amber-500/30"
        />
        <StatTile
          value={`${kbHitPct.toFixed(1)}%`}
          label="KB Hit Rate (fresh)"
          sublabel={`${d.kb.hit} of ${kbEscalated} escalated`}
          valueClass="text-purple-400"
          borderClass="border-purple-500/30"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <PipelineFunnel
          stages={[
            { label: 'Ingested', value: d.ingested },
            { label: 'Processed', value: d.processed },
            { label: 'Triaged', value: d.processed },
          ]}
          classifiedTotal={classifiedTotal}
          classifiedSegments={[
            { label: 'TP', value: d.classification.truePositive, colorClass: 'bg-red-500' },
            { label: 'FP', value: d.classification.falsePositive, colorClass: 'bg-emerald-500' },
            { label: 'Needs Review', value: d.classification.needsReview, colorClass: 'bg-amber-500' },
          ]}
        />
        <DonutChart
          title="Result Cache"
          centerValue={`${cacheHitPct.toFixed(0)}%`}
          centerLabel={`hit · TTL ${d.cache.ttlDays}d`}
          segments={[
            { label: 'Cache Hit', value: d.cache.hit, colorClass: 'text-blue-400' },
            { label: 'Cache Miss', value: d.cache.miss, colorClass: 'text-gray-700' },
          ]}
        />
        <DonutChart
          title="Knowledge Base Match"
          centerValue={`${kbHitPct.toFixed(0)}%`}
          centerLabel="of escalated"
          segments={[
            { label: 'KB Hit', value: d.kb.hit, colorClass: 'text-purple-400' },
            { label: 'KB Miss', value: d.kb.miss, colorClass: 'text-gray-700' },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DonutChart
          title="Classification Outcome"
          centerValue={classifiedTotal.toLocaleString()}
          centerLabel="classified"
          segments={[
            { label: 'True Positive', value: d.classification.truePositive, colorClass: 'text-red-400' },
            { label: 'False Positive', value: d.classification.falsePositive, colorClass: 'text-emerald-400' },
            { label: 'Needs Review', value: d.classification.needsReview, colorClass: 'text-amber-400' },
          ]}
        />
        <FPRateChart
          kbHitRate={d.fpRateByKb.kbHitRate}
          kbHitCount={d.fpRateByKb.kbHitCount}
          kbHitTotal={d.fpRateByKb.kbHitTotal}
          kbMissRate={d.fpRateByKb.kbMissRate}
          kbMissCount={d.fpRateByKb.kbMissCount}
          kbMissTotal={d.fpRateByKb.kbMissTotal}
        />
      </div>

      <KpiNotes
        notes={[
          `Cache TTL: ${d.cache.ttlDays} days. Repeat alerts get the prior verdict instantly.`,
          'KB Miss escalates to the LLM with no precedent — FP rate is highest here.',
        ]}
      />
    </div>
  )
}

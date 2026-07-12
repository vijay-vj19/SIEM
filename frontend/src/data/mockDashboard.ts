// Static illustrative figures for the Performance Dashboard mock view.
// These are NOT measured production data — the backend has no cache TTL,
// KB hit tracking, or escalation metrics wired up yet.

export interface DashboardMockData {
  ingested: number
  processed: number
  cache: { hit: number; miss: number; ttlDays: number }
  kb: { hit: number; miss: number }
  classification: { truePositive: number; falsePositive: number; needsReview: number }
  fpRateByKb: { kbHitRate: number; kbHitCount: number; kbHitTotal: number; kbMissRate: number; kbMissCount: number; kbMissTotal: number }
}

export const MOCK_DASHBOARD_DATA: DashboardMockData = {
  ingested: 1000,
  processed: 986,
  cache: { hit: 210, miss: 776, ttlDays: 30 },
  kb: { hit: 542, miss: 234 },
  classification: { truePositive: 172, falsePositive: 758, needsReview: 56 },
  fpRateByKb: {
    kbHitRate: 4.1,
    kbHitCount: 22,
    kbHitTotal: 542,
    kbMissRate: 9.8,
    kbMissCount: 23,
    kbMissTotal: 234,
  },
}

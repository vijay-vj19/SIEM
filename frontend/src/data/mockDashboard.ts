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
  ingested: 3150,
  processed: 3106,
  cache: { hit: 662, miss: 2444, ttlDays: 30 },
  kb: { hit: 1706, miss: 738 },
  classification: { truePositive: 541, falsePositive: 2389, needsReview: 176 },
  fpRateByKb: {
    kbHitRate: 4.1,
    kbHitCount: 70,
    kbHitTotal: 1706,
    kbMissRate: 9.8,
    kbMissCount: 72,
    kbMissTotal: 738,
  },
}

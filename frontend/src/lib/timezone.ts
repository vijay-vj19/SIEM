// The LLM Performance dashboard shows one canonical timezone for every
// viewer (rather than each analyst's own browser timezone), so a SOC team
// looking at the same run always sees the same timestamp.
//
// America/Chicago auto-handles the CST/CDT daylight-saving switch — it's
// CDT (UTC-5) roughly Mar-Nov and CST (UTC-6) the rest of the year.
export const DASHBOARD_TIMEZONE = 'America/Chicago'

export function dashboardTzAbbreviation(date: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: DASHBOARD_TIMEZONE,
    timeZoneName: 'short',
  }).formatToParts(date)
  return parts.find((p) => p.type === 'timeZoneName')?.value ?? 'CT'
}

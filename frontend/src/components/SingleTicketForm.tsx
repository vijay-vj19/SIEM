import { useState } from 'react'
import toast from 'react-hot-toast'
import { Send } from 'lucide-react'
import { triageSingle } from '../api/client'
import type { Ticket, TriageResponse } from '../types/ticket'

interface Props {
  onResults: (res: TriageResponse) => void
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const DEFAULTS: Ticket = {
  ticket_id: 'INC-2026-001',
  severity: 'HIGH',
  status: 'OPEN',
  created_time: new Date().toISOString(),
  rule_triggered: 'PowerShell Encoded Command Execution',
  mitre_attack: 'T1059.001',
  user: 'SVC-AnsibleDeploy',
  user_type: 'service_account',
  source_asset: 'MGMT-SRV-01',
  source_ip: '10.10.1.50',
  target_asset: 'APP-SRV-07',
  target_ip: '10.10.5.22',
  process: 'powershell.exe',
  command_line: 'powershell.exe -EncodedCommand JABzAD0...',
  decoded_command: 'w32tm.exe /query /status',
  hour_of_day: 2,
  day_of_week: 'Wednesday',
  historical_tp_count: 0,
  historical_fp_count: 47,
}

export function SingleTicketForm({ onResults }: Props) {
  const [form, setForm] = useState<Ticket>(DEFAULTS)
  const [loading, setLoading] = useState(false)

  const set = (field: keyof Ticket, value: unknown) =>
    setForm((f) => ({ ...f, [field]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await triageSingle(form)
      onResults(res)
      toast.success(`Ticket ${form.ticket_id} triaged`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Triage failed'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Row 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="label">Ticket ID *</label>
          <input className="input-field" value={form.ticket_id} onChange={(e) => set('ticket_id', e.target.value)} required />
        </div>
        <div>
          <label className="label">Severity *</label>
          <select className="input-field" value={form.severity} onChange={(e) => set('severity', e.target.value)} required>
            {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Rule Triggered *</label>
          <input className="input-field" value={form.rule_triggered} onChange={(e) => set('rule_triggered', e.target.value)} required />
        </div>
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="label">MITRE ATT&CK *</label>
          <input className="input-field" placeholder="e.g. T1059.001" value={form.mitre_attack} onChange={(e) => set('mitre_attack', e.target.value)} required />
        </div>
        <div>
          <label className="label">User *</label>
          <input className="input-field" value={form.user} onChange={(e) => set('user', e.target.value)} required />
        </div>
        <div>
          <label className="label">User Type *</label>
          <select className="input-field" value={form.user_type} onChange={(e) => set('user_type', e.target.value as Ticket['user_type'])} required>
            <option value="service_account">service_account</option>
            <option value="standard_user">standard_user</option>
            <option value="admin_user">admin_user</option>
          </select>
        </div>
      </div>

      {/* Row 3 — Assets */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Source Asset *</label>
            <input className="input-field" value={form.source_asset} onChange={(e) => set('source_asset', e.target.value)} required />
          </div>
          <div>
            <label className="label">Source IP *</label>
            <input className="input-field" value={form.source_ip} onChange={(e) => set('source_ip', e.target.value)} required />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Target Asset *</label>
            <input className="input-field" value={form.target_asset} onChange={(e) => set('target_asset', e.target.value)} required />
          </div>
          <div>
            <label className="label">Target IP *</label>
            <input className="input-field" value={form.target_ip} onChange={(e) => set('target_ip', e.target.value)} required />
          </div>
        </div>
      </div>

      {/* Row 4 — Process */}
      <div>
        <label className="label">Process *</label>
        <input className="input-field font-mono" value={form.process} onChange={(e) => set('process', e.target.value)} required />
      </div>
      <div>
        <label className="label">Command Line *</label>
        <textarea rows={2} className="input-field font-mono text-sm resize-none" value={form.command_line} onChange={(e) => set('command_line', e.target.value)} required />
      </div>
      <div>
        <label className="label">Decoded Command *</label>
        <textarea rows={2} className="input-field font-mono text-sm resize-none" value={form.decoded_command} onChange={(e) => set('decoded_command', e.target.value)} required />
      </div>

      {/* Row 5 — Timing */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <label className="label">Hour of Day *</label>
          <input type="number" min={0} max={23} className="input-field" value={form.hour_of_day} onChange={(e) => set('hour_of_day', Number(e.target.value))} required />
        </div>
        <div>
          <label className="label">Day of Week *</label>
          <select className="input-field" value={form.day_of_week} onChange={(e) => set('day_of_week', e.target.value)} required>
            {DAYS.map((d) => <option key={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Historical TPs *</label>
          <input type="number" min={0} className="input-field" value={form.historical_tp_count} onChange={(e) => set('historical_tp_count', Number(e.target.value))} required />
        </div>
        <div>
          <label className="label">Historical FPs *</label>
          <input type="number" min={0} className="input-field" value={form.historical_fp_count} onChange={(e) => set('historical_fp_count', Number(e.target.value))} required />
        </div>
      </div>

      <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
        <Send size={16} />
        {loading ? 'Running triage…' : 'Run Triage'}
      </button>
    </form>
  )
}

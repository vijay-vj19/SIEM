import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import * as XLSX from 'xlsx'
import toast from 'react-hot-toast'
import { Upload, FileSpreadsheet, X, ChevronRight } from 'lucide-react'
import { triageExcel } from '../api/client'
import type { TriageResponse } from '../types/ticket'

interface Props {
  onResults: (res: TriageResponse) => void
}

export function ExcelUpload({ onResults }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<{ headers: string[]; rows: Record<string, unknown>[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const parsePreview = (f: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const wb = XLSX.read(e.target?.result, { type: 'binary' })
        const ws = wb.Sheets[wb.SheetNames[0]]
        const data = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws)
        const headers = data.length > 0 ? Object.keys(data[0]) : []
        setPreview({ headers, rows: data.slice(0, 5) })
      } catch {
        toast.error('Failed to parse Excel file')
      }
    }
    reader.readAsBinaryString(f)
  }

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]
    if (!f) return
    setFile(f)
    parsePreview(f)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
  })

  const handleSubmit = async () => {
    if (!file) return
    setLoading(true)
    setProgress(10)

    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 5, 85))
    }, 800)

    try {
      const res = await triageExcel(file)
      setProgress(100)
      clearInterval(progressInterval)
      onResults(res)
      toast.success(`Processed ${res.results.length} ticket(s)`)
    } catch (err: unknown) {
      clearInterval(progressInterval)
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error ?? 'Upload failed'
      toast.error(msg)
    } finally {
      setLoading(false)
      setTimeout(() => setProgress(0), 1000)
    }
  }

  const clear = () => {
    setFile(null)
    setPreview(null)
    setProgress(0)
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 hover:border-gray-500'}`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-3 text-gray-500" size={36} />
        {isDragActive ? (
          <p className="text-blue-400 font-medium">Drop the file here…</p>
        ) : (
          <>
            <p className="text-gray-300 font-medium">Drag & drop an Excel file here</p>
            <p className="text-gray-500 text-sm mt-1">or click to browse — .xlsx / .xls only</p>
          </>
        )}
      </div>

      {/* File info */}
      {file && (
        <div className="flex items-center gap-3 bg-gray-800 rounded-lg px-4 py-3">
          <FileSpreadsheet size={20} className="text-emerald-400 shrink-0" />
          <span className="text-sm text-gray-200 flex-1 truncate">{file.name}</span>
          <span className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</span>
          <button onClick={clear} className="text-gray-500 hover:text-gray-300 transition-colors">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Preview table */}
      {preview && (
        <div>
          <p className="text-xs text-gray-400 mb-2">Preview — first 5 rows ({preview.headers.length} columns)</p>
          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="text-xs w-full">
              <thead className="bg-gray-800 text-gray-400">
                <tr>
                  {preview.headers.map((h) => (
                    <th key={h} className="px-3 py-2 text-left whitespace-nowrap font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {preview.rows.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-800/50">
                    {preview.headers.map((h) => (
                      <td key={h} className="px-3 py-2 text-gray-300 whitespace-nowrap max-w-[200px] truncate">
                        {String(row[h] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Progress bar */}
      {loading && (
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Submit */}
      {file && (
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="btn-primary flex items-center gap-2 w-full justify-center"
        >
          {loading ? 'Processing…' : 'Run Triage on All Tickets'}
          {!loading && <ChevronRight size={16} />}
        </button>
      )}
    </div>
  )
}

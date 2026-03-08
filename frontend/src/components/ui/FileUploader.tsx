import { useCallback, useRef, useState } from 'react'
import { Upload } from 'lucide-react'

interface FileUploaderProps {
  onFiles: (files: File[]) => void
  loading?: boolean
  accept?: string
}

export default function FileUploader({
  onFiles,
  loading,
  accept = '.xlsx,.xls,.csv',
}: FileUploaderProps) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return
      onFiles(Array.from(fileList))
    },
    [onFiles]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles]
  )

  return (
    <div
      onClick={() => !loading && inputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
        dragOver
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
          : 'border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500'
      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <Upload className="w-10 h-10 mx-auto mb-4 text-slate-400 dark:text-slate-500" />
      <p className="font-semibold text-slate-700 dark:text-slate-300">
        {loading ? 'Uploading…' : 'Drop file(s) here, or click to browse'}
      </p>
      <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
        Accepts <code>.xlsx</code> / <code>.xls</code> / <code>.csv</code> — single or multiple files merged automatically
      </p>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
        Daily: <strong>Date</strong>, <strong>Channel</strong>, <strong>Volume</strong> &nbsp;|&nbsp;
        Hourly: add <strong>Time</strong> column (HH:MM)
      </p>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
        Optional: <strong>AHT</strong> (avg handle time in seconds) &nbsp;&amp;&nbsp; <strong>Junior_Count</strong> or <strong>Junior_Ratio</strong>
      </p>
    </div>
  )
}

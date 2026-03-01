import { useCallback, useRef, useState } from 'react'
import { Upload } from 'lucide-react'

interface FileUploaderProps {
  onFile: (file: File) => void
  loading?: boolean
  accept?: string
}

export default function FileUploader({
  onFile,
  loading,
  accept = '.xlsx,.xls',
}: FileUploaderProps) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) onFile(file)
    },
    [onFile]
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
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) onFile(f)
        }}
      />
      <Upload className="w-10 h-10 mx-auto mb-4 text-slate-400 dark:text-slate-500" />
      <p className="font-semibold text-slate-700 dark:text-slate-300">
        {loading ? 'Uploading…' : 'Drop your Excel file here, or click to browse'}
      </p>
      <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
        Accepts <code>.xlsx</code> / <code>.xls</code> — requires{' '}
        <strong>Date</strong>, <strong>Channel</strong>, <strong>Volume</strong> columns
      </p>
    </div>
  )
}

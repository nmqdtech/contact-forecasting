import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronDown, FolderOpen, Plus, Trash2 } from 'lucide-react'
import { createProject, deleteProject, listProjects } from '../../api/projects'
import { useAppStore } from '../../store/useAppStore'
import type { Project } from '../../types'

export default function ProjectSelector() {
  const qc = useQueryClient()
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const setActiveProjectId = useAppStore((s) => s.setActiveProjectId)

  const [open, setOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [createError, setCreateError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: listProjects,
    staleTime: 30_000,
  })

  // Auto-select first project on load
  useEffect(() => {
    if (!activeProjectId && projects.length > 0) {
      setActiveProjectId(projects[0].id)
    }
  }, [projects, activeProjectId, setActiveProjectId])

  // Focus input when create row appears
  useEffect(() => {
    if (creating) inputRef.current?.focus()
  }, [creating])

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ['channels'] })
    qc.invalidateQueries({ queryKey: ['channel-data'] })
    qc.invalidateQueries({ queryKey: ['forecast'] })
    qc.invalidateQueries({ queryKey: ['forecast-monthly'] })
    qc.invalidateQueries({ queryKey: ['backtest'] })
    qc.invalidateQueries({ queryKey: ['seasonality'] })
    qc.invalidateQueries({ queryKey: ['summary'] })
    qc.invalidateQueries({ queryKey: ['datasets'] })
  }

  const createMut = useMutation({
    mutationFn: createProject,
    onSuccess: (proj) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      setActiveProjectId(proj.id)
      invalidateAll()
      setCreating(false)
      setNewName('')
      setCreateError('')
      setOpen(false)
    },
    onError: (err: any) =>
      setCreateError(err?.response?.data?.detail ?? 'Failed to create project'),
  })

  const deleteMut = useMutation({
    mutationFn: deleteProject,
    onSuccess: (_, deletedId) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      if (activeProjectId === deletedId) {
        const remaining = projects.filter((p) => p.id !== deletedId)
        setActiveProjectId(remaining[0]?.id ?? null)
        invalidateAll()
      }
    },
  })

  const handleSwitch = (id: string) => {
    if (id === activeProjectId) { setOpen(false); return }
    setActiveProjectId(id)
    invalidateAll()
    setOpen(false)
  }

  const handleCreate = () => {
    const name = newName.trim()
    if (!name) return
    createMut.mutate({ name })
  }

  const activeProject = projects.find((p) => p.id === activeProjectId)

  return (
    <div className="relative px-3">
      {/* Trigger */}
      <button
        onClick={() => { setOpen((o) => !o); setCreating(false) }}
        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
      >
        <FolderOpen className="w-4 h-4 flex-shrink-0 text-blue-400" />
        <span className="flex-1 truncate text-left font-medium">
          {activeProject?.name ?? 'Select project'}
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 flex-shrink-0 text-slate-500 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => { setOpen(false); setCreating(false); setNewName('') }}
          />
          <div className="absolute left-3 right-3 top-full mt-1 z-50 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
            {/* Project list */}
            {projects.map((p) => (
              <div
                key={p.id}
                className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 transition-colors group cursor-pointer"
                onClick={() => handleSwitch(p.id)}
              >
                <span className="w-4 flex-shrink-0 flex items-center justify-center">
                  {p.id === activeProjectId && (
                    <Check className="w-3.5 h-3.5 text-blue-400" />
                  )}
                </span>
                <span
                  className={`flex-1 truncate text-sm ${
                    p.id === activeProjectId
                      ? 'text-white font-medium'
                      : 'text-slate-300'
                  }`}
                >
                  {p.name}
                </span>
                {projects.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm(`Delete "${p.name}"? Its data will be unlinked.`))
                        deleteMut.mutate(p.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all flex-shrink-0 p-0.5"
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}

            {/* Divider + create row */}
            <div className="border-t border-slate-700">
              {creating ? (
                <div className="flex items-center gap-1.5 px-2 py-2">
                  <input
                    ref={inputRef}
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreate()
                      if (e.key === 'Escape') { setCreating(false); setNewName(''); setCreateError('') }
                    }}
                    placeholder="Project name…"
                    className="flex-1 min-w-0 bg-slate-900 text-white text-xs px-2 py-1.5 rounded-lg border border-slate-600 focus:outline-none focus:border-blue-500 placeholder:text-slate-500"
                  />
                  <button
                    onClick={handleCreate}
                    disabled={!newName.trim() || createMut.isPending}
                    className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors flex-shrink-0"
                  >
                    {createMut.isPending ? '…' : 'Add'}
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setCreating(true)}
                  disabled={projects.length >= 5}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Plus className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{projects.length >= 5 ? 'Max 5 projects reached' : 'New project'}</span>
                </button>
              )}
              {createError && (
                <p className="px-3 pb-2 text-xs text-red-400">{createError}</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

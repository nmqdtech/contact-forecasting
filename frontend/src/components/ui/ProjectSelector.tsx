import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen, Plus, Trash2, X } from 'lucide-react'
import { createProject, deleteProject, listProjects } from '../../api/projects'
import { useAppStore } from '../../store/useAppStore'
import type { Project } from '../../types'

export default function ProjectSelector() {
  const qc = useQueryClient()
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const setActiveProjectId = useAppStore((s) => s.setActiveProjectId)

  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [createError, setCreateError] = useState('')

  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: listProjects,
    staleTime: 30_000,
  })

  // Auto-select the first project on load if none is selected
  useEffect(() => {
    if (!activeProjectId && projects.length > 0) {
      setActiveProjectId(projects[0].id)
    }
  }, [projects, activeProjectId, setActiveProjectId])

  const createMut = useMutation({
    mutationFn: createProject,
    onSuccess: (proj) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      setActiveProjectId(proj.id)
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      setCreateError('')
      // Invalidate all data queries since project changed
      qc.invalidateQueries({ queryKey: ['channels'] })
      qc.invalidateQueries({ queryKey: ['forecast'] })
    },
    onError: (err: any) =>
      setCreateError(err?.response?.data?.detail || 'Failed to create project'),
  })

  const deleteMut = useMutation({
    mutationFn: deleteProject,
    onSuccess: (_, deletedId) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      if (activeProjectId === deletedId) {
        const remaining = projects.filter((p) => p.id !== deletedId)
        setActiveProjectId(remaining[0]?.id ?? null)
        qc.invalidateQueries({ queryKey: ['channels'] })
        qc.invalidateQueries({ queryKey: ['forecast'] })
      }
    },
  })

  const activeProject = projects.find((p) => p.id === activeProjectId)

  function handleSwitch(id: string) {
    if (id === activeProjectId) return
    setActiveProjectId(id)
    qc.invalidateQueries({ queryKey: ['channels'] })
    qc.invalidateQueries({ queryKey: ['forecast'] })
    qc.invalidateQueries({ queryKey: ['forecast-monthly'] })
    qc.invalidateQueries({ queryKey: ['backtest'] })
    qc.invalidateQueries({ queryKey: ['seasonality'] })
    qc.invalidateQueries({ queryKey: ['channel-data'] })
  }

  return (
    <div className="px-3 pb-3">
      {/* Active project display */}
      <div className="flex items-center gap-2 mb-1.5">
        <FolderOpen className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        <span className="text-xs text-slate-400 uppercase tracking-wide font-medium">Project</span>
      </div>

      {/* Project list */}
      <div className="space-y-0.5">
        {projects.map((p) => (
          <div
            key={p.id}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors group ${
              p.id === activeProjectId
                ? 'bg-blue-600/20 text-blue-300'
                : 'text-slate-400 hover:bg-white/5 hover:text-white'
            }`}
            onClick={() => handleSwitch(p.id)}
          >
            <span className="flex-1 truncate">{p.name}</span>
            {projects.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (confirm(`Delete project "${p.name}"? All its data will be unlinked.`))
                    deleteMut.mutate(p.id)
                }}
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all flex-shrink-0"
                title="Delete project"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Create new project */}
      {projects.length < 5 && !showCreate && (
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 mt-1.5 px-2.5 py-1.5 rounded-lg text-xs text-slate-500 hover:text-white hover:bg-white/5 transition-colors w-full"
        >
          <Plus className="w-3 h-3" />
          New project
        </button>
      )}

      {showCreate && (
        <div className="mt-2 rounded-lg bg-white/5 p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-300">New Project</span>
            <button
              onClick={() => { setShowCreate(false); setCreateError('') }}
              className="text-slate-500 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {createError && (
            <p className="text-xs text-red-400">{createError}</p>
          )}
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Project name"
            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            onKeyDown={(e) => e.key === 'Enter' && newName.trim() && createMut.mutate({ name: newName.trim(), description: newDesc || undefined })}
          />
          <input
            type="text"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={() => newName.trim() && createMut.mutate({ name: newName.trim(), description: newDesc || undefined })}
            disabled={createMut.isPending || !newName.trim()}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-medium py-1 rounded transition-colors"
          >
            {createMut.isPending ? 'Creating…' : 'Create'}
          </button>
        </div>
      )}
    </div>
  )
}

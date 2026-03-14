import client from './client'
import type { Project, ProjectCreate } from '../types'

export const listProjects = async (): Promise<Project[]> => {
  const { data } = await client.get<Project[]>('/projects')
  return data
}

export const createProject = async (body: ProjectCreate): Promise<Project> => {
  const { data } = await client.post<Project>('/projects', body)
  return data
}

export const updateProject = async (
  id: string,
  body: { name?: string; description?: string }
): Promise<Project> => {
  const { data } = await client.patch<Project>(`/projects/${id}`, body)
  return data
}

export const deleteProject = async (id: string): Promise<void> => {
  await client.delete(`/projects/${id}`)
}

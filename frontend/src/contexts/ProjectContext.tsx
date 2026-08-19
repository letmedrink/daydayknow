import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { fetchProjects, createProject, deleteProject, deleteProjectData, importProject } from '../lib/api';

export interface Project {
  id: string;
  name: string;
  path: string;
  createdAt: string;
  managed?: boolean;
}

interface ProjectContextType {
  projects: Project[];
  activeProjectId: string;
  setActiveProject: (id: string) => void;
  createProject: (name: string, path?: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  deleteProjectData: (id: string, confirmation: string) => Promise<void>;
  refreshProjects: () => Promise<void>;
  importProject: (file: File, name?: string) => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string>('');

  const refreshProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
      // 如果当前激活项目不存在，切到 default
      if (activeProjectId && !data.find((p: Project) => p.id === activeProjectId)) {
        setActiveProjectId('');
      }
    } catch (e) {
      console.error('Failed to load projects:', e);
    }
  }, [activeProjectId]);

  useEffect(() => { refreshProjects(); }, []);

  const handleCreate = useCallback(async (name: string, path?: string) => {
    await createProject(name, path);
    await refreshProjects();
  }, [refreshProjects]);

  const handleDelete = useCallback(async (id: string) => {
    await deleteProject(id);
    if (activeProjectId === id) {
      setActiveProjectId('');
    }
    await refreshProjects();
  }, [activeProjectId, refreshProjects]);

  const handleDeleteData = useCallback(async (id: string, confirmation: string) => {
    await deleteProjectData(id, confirmation);
    if (activeProjectId === id) setActiveProjectId('');
    await refreshProjects();
  }, [activeProjectId, refreshProjects]);

  const handleImport = useCallback(async (file: File, name?: string) => {
    await importProject(file, name);
    await refreshProjects();
  }, [refreshProjects]);

  return (
    <ProjectContext.Provider value={{
      projects,
      activeProjectId,
      setActiveProject: setActiveProjectId,
      createProject: handleCreate,
      deleteProject: handleDelete,
      deleteProjectData: handleDeleteData,
      refreshProjects, importProject: handleImport,
    }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error('useProject must be used within ProjectProvider');
  return ctx;
}

import { useRef, useState } from 'react';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';
import { exportProject } from '../lib/api';

export function ProjectHome({ onEnter }: { onEnter: () => void }) {
  const { projects, setActiveProject, createProject, deleteProject, deleteProjectData, importProject } = useProject();
  const [newName, setNewName] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const importRef = useRef<HTMLInputElement>(null);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError('');
    try {
      await createProject(newName.trim());
      setNewName('');
      setShowCreate(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('仅从项目列表移除？磁盘数据会保留。')) return;
    await deleteProject(id);
  };

  const handlePermanentDelete = async (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation();
    const confirmation = window.prompt(`永久删除会移除全部 Wiki 和对话，且无法恢复。请输入项目名“${name}”确认：`);
    if (confirmation !== name) return;
    await deleteProjectData(id, confirmation);
  };

  const handleOpen = (id: string) => {
    setActiveProject(id);
    onEnter();
  };

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <h1 style={styles.title}>LLM Wiki</h1>
        <p style={styles.subtitle}>用 LLM 构建和维护你的个人知识库</p>

        {projects.length > 0 && (
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>项目列表</h2>
            <div style={styles.projectList}>
              {projects.map((p) => (
                <div
                  key={p.id}
                  style={styles.projectCard}
                  onClick={() => handleOpen(p.id)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = theme.accent;
                    e.currentTarget.style.boxShadow = theme.shadow.md;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = theme.border.light;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={styles.projectHeader}>
                    <span style={styles.projectName}>{p.name}</span>
                    <span style={styles.actions}>
                      <button style={styles.removeBtn} onClick={(e) => handleDelete(e, p.id)}>从列表移除</button>
                      {p.managed && (
                        <button style={styles.deleteBtn} onClick={(e) => handlePermanentDelete(e, p.id, p.name)}>永久删除</button>
                      )}
                      <button style={styles.removeBtn} onClick={(e) => { e.stopPropagation(); void exportProject(p.id, p.name); }}>导出</button>
                    </span>
                  </div>
                  <span style={styles.projectPath}>{p.path}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {showCreate ? (
          <div style={styles.createForm}>
            <input
              style={styles.input}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="项目名称"
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setShowCreate(false); }}
              autoFocus
            />
            <div style={styles.createActions}>
              <button style={styles.cancelBtn} onClick={() => setShowCreate(false)}>取消</button>
              <button style={styles.createBtn} onClick={handleCreate} disabled={creating || !newName.trim()}>
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
            {error && <p role="alert" style={styles.error}>{error}</p>}
          </div>
        ) : (
          <button style={styles.newBtn} onClick={() => setShowCreate(true)}>
            + 新建项目
          </button>
        )}
        <button style={{ ...styles.newBtn, marginTop: 8 }} onClick={() => importRef.current?.click()}>导入项目 ZIP</button>
        <input ref={importRef} type="file" accept=".zip,application/zip" style={{ display: 'none' }} onChange={(event) => { const file = event.target.files?.[0]; if (file) void importProject(file); event.currentTarget.value = ''; }} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100vw', height: '100vh',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    backgroundColor: theme.bg.window, fontFamily: theme.font,
  },
  content: { width: 460, maxWidth: '90vw' },
  title: {
    fontSize: 32, fontWeight: 700, color: theme.text.primary,
    margin: '0 0 8px', letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: 15, color: theme.text.secondary,
    margin: '0 0 40px', lineHeight: 1.5,
  },
  section: { marginBottom: 32 },
  sectionTitle: {
    fontSize: 13, fontWeight: 600, color: theme.text.tertiary,
    textTransform: 'uppercase', letterSpacing: '0.5px', margin: '0 0 12px',
  },
  projectList: { display: 'flex', flexDirection: 'column', gap: 8 },
  projectCard: {
    padding: '14px 16px', backgroundColor: theme.bg.content,
    border: `1px solid ${theme.border.light}`, borderRadius: theme.radius.md,
    cursor: 'pointer', transition: 'all 0.15s',
  },
  projectHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4,
  },
  projectName: { fontSize: 15, fontWeight: 600, color: theme.text.primary },
  actions: { display: 'flex', gap: 6 },
  removeBtn: { fontSize: 12, color: theme.text.secondary, cursor: 'pointer', padding: '2px 8px', border: 'none', background: 'transparent' },
  deleteBtn: { fontSize: 12, color: '#c0392b', cursor: 'pointer', padding: '2px 8px', border: 'none', background: 'transparent' },
  projectPath: {
    fontSize: 12, color: theme.text.tertiary, fontFamily: theme.fontMono,
  },
  newBtn: {
    fontSize: 14, fontWeight: 600, padding: '10px 20px',
    border: `1px dashed ${theme.border.medium}`, borderRadius: theme.radius.md,
    backgroundColor: 'transparent', color: theme.text.secondary,
    cursor: 'pointer', width: '100%', transition: 'all 0.15s',
  },
  createForm: {
    padding: '16px', backgroundColor: theme.bg.content,
    border: `1px solid ${theme.border.light}`, borderRadius: theme.radius.md,
  },
  input: {
    width: '100%', fontSize: 14, padding: '10px 14px',
    border: `1px solid ${theme.border.light}`, borderRadius: theme.radius.md,
    outline: 'none', fontFamily: theme.font, backgroundColor: theme.bg.raised,
    boxSizing: 'border-box',
  },
  createActions: {
    display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12,
  },
  cancelBtn: {
    fontSize: 13, padding: '7px 16px', border: 'none',
    borderRadius: theme.radius.sm, backgroundColor: 'transparent',
    color: theme.text.secondary, cursor: 'pointer',
  },
  createBtn: {
    fontSize: 13, fontWeight: 600, padding: '7px 16px', border: 'none',
    borderRadius: theme.radius.sm, backgroundColor: theme.accent,
    color: '#fff', cursor: 'pointer',
  },
  error: { margin: '10px 0 0', color: '#b42318', fontSize: 12, lineHeight: 1.5 },
};

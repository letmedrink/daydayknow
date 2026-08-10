import { useState, useEffect, useCallback } from 'react';
import { fetchWikiPages } from '../lib/api';
import { usePreview } from '../contexts/PreviewContext';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';
import type { WikiPage } from '../types';

export function WikiTree({ onBack }: { onBack?: () => void }) {
  const [tree, setTree] = useState<WikiPage[]>([]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const { activePath, openPreview, setActivePath } = usePreview();
  const { projects, activeProjectId } = useProject();

  const currentProject = projects.find((p) => p.id === activeProjectId);

  useEffect(() => {
    fetchWikiPages(activeProjectId)
      .then((data) => setTree(data.tree))
      .catch(console.error);
  }, [activeProjectId]);

  const toggleDir = useCallback((path: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path); else next.add(path);
      return next;
    });
  }, []);

  const handleSelect = useCallback((path: string) => {
    setActivePath(path);
    openPreview(path);
  }, [setActivePath, openPreview]);

  const renderTree = (items: WikiPage[], depth = 0) => {
    return items.map((item) => {
      const isDir = item.is_dir;
      const isCollapsed = collapsed.has(item.path);
      const isActive = activePath === item.path;

      return (
        <div key={item.path}>
          <div
            style={{
              ...styles.treeItem,
              paddingLeft: 8 + depth * 18,
              ...(isActive ? styles.treeItemActive : {}),
            }}
            onClick={() => {
              if (isDir) toggleDir(item.path);
              else handleSelect(item.path);
            }}
          >
            {isDir ? (
              <span style={{
                ...styles.arrow,
                transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
              }}>▾</span>
            ) : (
              <span style={styles.fileIcon}>📄</span>
            )}
            <span style={styles.itemLabel}>{item.name}</span>
          </div>
          {isDir && !isCollapsed && item.children && renderTree(item.children, depth + 1)}
        </div>
      );
    });
  };

  return (
    <div style={styles.container}>
      {/* 项目名 + 返回按钮 */}
      <div style={styles.projectBar}>
        <span style={styles.backBtn} onClick={onBack} title="返回项目列表">←</span>
        <span style={styles.projectName}>📂 {currentProject?.name || '项目'}</span>
      </div>

      <div style={styles.header}>
        <span style={styles.title}>🌳 知识树</span>
      </div>
      <div style={styles.tree}>
        {tree.length === 0 ? (
          <p style={styles.empty}>暂无页面</p>
        ) : (
          renderTree(tree)
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100%',
    minWidth: 0,
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: theme.bg.sidebar,
    borderRight: `1px solid ${theme.border.light}`,
    fontFamily: theme.font,
  },
  projectBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 12px',
    borderBottom: `1px solid ${theme.border.light}`,
  },
  backBtn: {
    fontSize: 16,
    color: theme.text.tertiary,
    cursor: 'pointer',
    padding: '2px 4px',
    borderRadius: 4,
    lineHeight: 1,
    transition: 'color 0.15s',
  },
  projectName: {
    fontSize: 13,
    fontWeight: 600,
    color: theme.text.primary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  header: {
    padding: '14px 14px 10px',
    borderBottom: `1px solid ${theme.border.light}`,
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: theme.text.primary,
  },
  tree: {
    flex: 1,
    overflowY: 'auto',
    padding: '4px 0',
  },
  treeItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '5px 8px',
    cursor: 'pointer',
    fontSize: 14,
    color: theme.text.primary,
    borderRadius: theme.radius.sm,
    margin: '0 6px',
    transition: 'background-color 0.1s',
    userSelect: 'none',
  },
  treeItemActive: {
    backgroundColor: theme.accentBg,
    color: theme.accent,
    fontWeight: 600,
  },
  arrow: {
    fontSize: 10,
    color: theme.text.tertiary,
    transition: 'transform 0.15s ease',
    width: 14,
    textAlign: 'center',
    flexShrink: 0,
  },
  fileIcon: {
    fontSize: 13,
    width: 14,
    textAlign: 'center',
    flexShrink: 0,
    lineHeight: 1,
  },
  itemLabel: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  empty: { padding: 16, color: theme.text.tertiary, fontSize: 13, textAlign: 'center' },
};

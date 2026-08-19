import { useLocation, useNavigate } from 'react-router-dom';
import { theme } from '../lib/theme';

const NAV_ITEMS = [
  { path: '/', label: '对话', icon: '💬' },
  { path: '/ingest', label: '摄入', icon: '📄' },
  { path: '/reviews', label: '审阅', icon: '📋' },
  { path: '/research', label: '研究', icon: '🔍' },
  { path: '/tasks', label: '任务', icon: '☷' },
  { path: '/graph', label: '图谱', icon: '◈' },
  { path: '/settings', label: '设置', icon: '⚙' },
];

export function ContentNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  const isActive = (itemPath: string) => {
    if (itemPath === '/') return path === '/';
    return path.startsWith(itemPath);
  };

  return (
    <div style={styles.bar}>
      {NAV_ITEMS.map((item) => {
        const active = isActive(item.path);
        return (
          <button
            key={item.path}
            style={{
              ...styles.tab,
              ...(active ? styles.tabActive : {}),
            }}
            onClick={() => navigate(item.path)}
          >
            <span style={styles.icon}>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: 1,
    padding: '0 12px',
    height: 38,
    minHeight: 38,
    backgroundColor: theme.bg.header,
    borderBottom: `1px solid ${theme.border.light}`,
    fontFamily: theme.font,
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '5px 10px',
    border: 'none',
    borderRadius: theme.radius.sm,
    backgroundColor: 'transparent',
    color: theme.text.secondary,
    fontSize: 12,
    cursor: 'pointer',
    transition: 'all 0.12s',
    fontWeight: 500,
    fontFamily: theme.font,
  },
  tabActive: {
    backgroundColor: theme.accentBg,
    color: theme.accent,
    fontWeight: 600,
  },
  icon: { fontSize: 13 },
};

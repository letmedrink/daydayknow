import { useNavigate, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: '对话', icon: '💬' },
  { path: '/graph', label: '图谱', icon: '◈' },
  { path: '/profile', label: '画像', icon: '◉' },
  { path: '/import', label: '导入', icon: '⬆' },
];

export function NavRail() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div style={styles.rail}>
      <div style={styles.brand}>知</div>
      <div style={styles.items}>
        {NAV_ITEMS.map((item) => {
          const active = item.path === '/'
            ? location.pathname === '/' || location.pathname === '/conv'
            : location.pathname === item.path;
          return (
            <button
              key={item.path}
              style={{
                ...styles.navBtn,
                ...(active ? styles.navBtnActive : {}),
              }}
              onClick={() => navigate(item.path)}
              title={item.label}
            >
              <span style={styles.icon}>{item.icon}</span>
              <span style={styles.label}>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  rail: {
    width: 64,
    minWidth: 64,
    height: '100vh',
    backgroundColor: '#4a443d',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '12px 0',
    gap: 4,
  },
  brand: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 16,
    fontWeight: 700,
    marginBottom: 16,
  },
  items: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    width: '100%',
    padding: '0 8px',
    boxSizing: 'border-box',
  },
  navBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
    padding: '8px 0',
    border: 'none',
    borderRadius: 8,
    backgroundColor: 'transparent',
    color: '#9a9088',
    cursor: 'pointer',
    fontSize: 10,
    transition: 'background-color 0.15s, color 0.15s',
  },
  navBtnActive: {
    backgroundColor: '#58524a',
    color: '#e8e0d8',
  },
  icon: {
    fontSize: 18,
    lineHeight: 1,
  },
  label: {
    fontSize: 10,
    lineHeight: 1,
  },
};

import type { Conversation } from '../types';

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins}分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `${days}天前`;
}

interface ConversationPanelProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export function ConversationPanel({ conversations, activeId, onSelect, onNew, onDelete }: ConversationPanelProps) {
  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.headerTitle}>对话</span>
        <button style={styles.newBtn} onClick={onNew}>
          + 新建
        </button>
      </div>

      <div style={styles.list}>
        {conversations.length === 0 && (
          <div style={styles.empty}>暂无对话记录</div>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            style={{
              ...styles.item,
              ...(activeId === conv.id ? styles.itemActive : {}),
            }}
            onClick={() => onSelect(conv.id)}
          >
            <div style={styles.itemTitle}>{conv.title || '新对话'}</div>
            <div style={styles.itemMeta}>
              <span>{conv.message_count}条消息</span>
              <span>{timeAgo(conv.updated_at)}</span>
              <button
                style={styles.deleteBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 240,
    minWidth: 240,
    height: '100vh',
    backgroundColor: '#58524a',
    display: 'flex',
    flexDirection: 'column',
    color: '#e8e0d8',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 12px 8px',
  },
  headerTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#b0a89e',
  },
  newBtn: {
    padding: '4px 10px',
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    border: 'none',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: '0 8px 8px',
  },
  empty: {
    textAlign: 'center',
    padding: '20px',
    color: '#9a9088',
    fontSize: 13,
  },
  item: {
    padding: '10px 12px',
    borderRadius: 8,
    cursor: 'pointer',
    marginBottom: 2,
    transition: 'background-color 0.15s',
  },
  itemActive: {
    backgroundColor: '#6b645c',
  },
  itemTitle: {
    fontSize: 14,
    fontWeight: 500,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    marginBottom: 4,
  },
  itemMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 11,
    color: '#9a9088',
  },
  deleteBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    color: '#8a8078',
    fontSize: 16,
    cursor: 'pointer',
    padding: '0 4px',
    lineHeight: 1,
  },
};

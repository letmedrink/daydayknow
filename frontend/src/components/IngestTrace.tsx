import type { IngestTraceEvent } from '../types';
import { theme } from '../lib/theme';

const STAGE_ICONS: Record<string, string> = {
  parse: '📄', source: '🗄️', cache: '⚡', images: '🖼️', index: '📚',
  analyze: '🧠', retrieve: '🔎', generate: '✨', review: '✅',
};

export function IngestTrace({ events }: { events: IngestTraceEvent[] }) {
  if (!events.length) return null;
  const startedAt = events[0].timestamp;
  return <details open style={styles.container}>
    <summary style={styles.summary}>详细处理链路 · {events.length} 条事件</summary>
    <div style={styles.timeline}>
      {events.map((event, index) => <div key={`${event.timestamp}-${event.title}-${index}`} style={styles.event}>
        <div style={{ ...styles.dot, ...(index === events.length - 1 ? styles.activeDot : {}) }}>{STAGE_ICONS[event.stage] || '•'}</div>
        <div style={styles.eventBody}>
          <div style={styles.eventHeader}>
            <strong style={styles.eventTitle}>{event.title}</strong>
            <span style={styles.time}>+{((event.timestamp - startedAt) / 1000).toFixed(1)}s</span>
          </div>
          {event.message && <div style={styles.message}>{event.message}</div>}
          {event.meta && event.meta.length > 0 && <div style={styles.metaList}>
            {event.meta.map((item, metaIndex) => <span key={`${item.label}-${metaIndex}`} style={styles.meta} title={item.value}>
              <span style={styles.metaLabel}>{item.label}</span> {item.value}
            </span>)}
          </div>}
        </div>
      </div>)}
    </div>
  </details>;
}

const styles: Record<string, React.CSSProperties> = {
  container: { marginTop: 12, border: `1px solid ${theme.border.light}`, borderRadius: theme.radius.md, background: theme.bg.raised },
  summary: { padding: '10px 12px', cursor: 'pointer', color: theme.text.primary, fontSize: 13, fontWeight: 600, userSelect: 'none' },
  timeline: { position: 'relative', padding: '2px 12px 12px 42px' },
  event: { position: 'relative', minHeight: 44, padding: '4px 0 10px', borderLeft: `1px solid ${theme.border.medium}` },
  dot: { position: 'absolute', left: -15, top: 2, width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', background: theme.bg.content, border: `1px solid ${theme.border.medium}`, fontSize: 13 },
  activeDot: { borderColor: theme.accent, boxShadow: `0 0 0 3px ${theme.accentBg}` },
  eventBody: { paddingLeft: 20, minWidth: 0 },
  eventHeader: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10 },
  eventTitle: { color: theme.text.primary, fontSize: 12 },
  time: { color: theme.text.tertiary, fontSize: 10, fontFamily: theme.fontMono, whiteSpace: 'nowrap' },
  message: { color: theme.text.secondary, fontSize: 11, marginTop: 2 },
  metaList: { display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 6 },
  meta: { maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '2px 6px', borderRadius: 4, background: theme.bg.content, border: `1px solid ${theme.border.light}`, color: theme.text.secondary, fontSize: 10, fontFamily: theme.fontMono },
  metaLabel: { color: theme.text.tertiary, fontFamily: theme.font },
};

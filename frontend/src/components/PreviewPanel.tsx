import { useEffect, useState, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { usePreview } from '../contexts/PreviewContext';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';
import { fetchWikiPage, fetchWikiPages } from '../lib/api';
import type { WikiPage } from '../types';

/** 按 [[wikilink]] 拆分文本，返回 text/link 段 */
function splitWikilinks(text: string): Array<{ type: 'text' | 'link'; content: string }> {
  const parts: Array<{ type: 'text' | 'link'; content: string }> = [];
  const regex = /\[\[([^\]]+)\]\]/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: 'link', content: match[1] });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIndex) });
  }
  return parts;
}

/** 解析 wikilink 目标，支持标题/名称/路径模糊匹配 */
function resolveWikiTarget(target: string, pages: WikiPage[]): string {
  if (pages.some((p) => p.path === target)) return target;
  const byTitle = pages.find(
    (p) => p.title === target || p.name.replace(/\.md$/, '') === target,
  );
  if (byTitle) return byTitle.path;
  const fuzzy = pages.find(
    (p) => p.title?.includes(target) || p.path.includes(target),
  );
  return fuzzy?.path ?? target;
}

const TYPE_COLORS: Record<string, string> = {
  entity: '#007AFF',
  concept: '#AF52DE',
  source: '#FF9500',
  event: '#FF3B30',
  person: '#34C759',
  note: '#636366',
};

const TYPE_LABELS: Record<string, string> = {
  entity: '实体',
  concept: '概念',
  source: '来源',
  comparison: '对比',
  query: '问题',
  synthesis: '综合',
  finding: '发现',
  thesis: '论点',
  methodology: '方法',
  event: '事件',
  person: '人物',
  note: '笔记',
};

export function PreviewPanel() {
  const { activePath, closePreview, setActivePath, openPreview } = usePreview();
  const { activeProjectId } = useProject();
  const [content, setContent] = useState('');
  const [fm, setFm] = useState<{
    title?: string;
    type: string;
    tags: string[];
    sources: string[];
    related: string[];
    created?: string;
    updated?: string;
  } | null>(null);
  const [allPages, setAllPages] = useState<WikiPage[]>([]);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Load page list for wikilink resolution
  const loadPages = useCallback(() => {
    fetchWikiPages(activeProjectId).then((data) => {
        const flatten = (items: WikiPage[]): WikiPage[] =>
          items.flatMap((i) => (i.is_dir ? flatten(i.children || []) : [i]));
        setAllPages(flatten(data.tree));
      }).catch(console.error);
  }, [activeProjectId]);

  useEffect(() => { loadPages(); }, [loadPages]);

  // 监听页面列表更新事件（摄入完成后触发）
  useEffect(() => {
    const handler = () => loadPages();
    window.addEventListener('wikiPagesUpdated', handler);
    return () => window.removeEventListener('wikiPagesUpdated', handler);
  }, [loadPages]);

  useEffect(() => {
    if (!activePath) return;
    fetchWikiPage(activePath, activeProjectId)
        .then((data) => {
          const fm = data.frontmatter;
          const hasFm = fm && Object.keys(fm).length > 0;
          // 无 frontmatter 时用文件名作标题
          const fallbackTitle = activePath?.split('/').pop()?.replace(/\.md$/, '') || 'Untitled';
          setFm({
            title: hasFm ? (fm.title || fallbackTitle) : fallbackTitle,
            type: hasFm ? (fm.type || '') : '',
            tags: hasFm ? (fm.tags || []) : [],
            sources: hasFm ? (fm.sources || []) : [],
            related: hasFm ? (fm.related || []) : [],
            created: hasFm ? fm.created : undefined,
            updated: hasFm ? fm.updated : undefined,
          });
          setContent(data.body || '');
        })
        .catch(console.error);
    bodyRef.current?.scrollTo(0, 0);
  }, [activePath, activeProjectId]);

  const resolveTarget = (name: string) => resolveWikiTarget(name, allPages);

  const handleClickLink = (target: string) => {
    const resolved = resolveTarget(target);
    if (resolved) {
      setActivePath(resolved);
      openPreview(resolved);
    }
  };

  if (!activePath) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>📄</div>
        <div style={styles.emptyText}>选择页面预览</div>
      </div>
    );
  }

  const typeColor = fm ? (TYPE_COLORS[fm.type] || theme.text.secondary) : theme.text.secondary;
  const segments = splitWikilinks(content);

  return (
    <div style={styles.container}>
      {/* Header: 文件路径 + 关闭按钮 */}
      <div style={styles.header}>
        <span style={styles.filePath} title={activePath}>
          {activePath}
        </span>
        <button style={styles.closeBtn} onClick={closePreview}>
          ✕
        </button>
      </div>

      {/* Body: 结构化元数据 + 正文 */}
      <div ref={bodyRef} style={styles.body}>
        {/* 标题 + 类型标签（同行） */}
        {fm && (
          <div style={styles.frontmatter}>
            <div style={styles.titleRow}>
              <h1 style={styles.title}>{fm.title || 'Untitled'}</h1>
              {fm.type && (
                <span
                  style={{
                    ...styles.typeBadge,
                    backgroundColor: typeColor + '18',
                    color: typeColor,
                    borderColor: typeColor + '40',
                  }}
                >
                  {TYPE_LABELS[fm.type] || fm.type}
                </span>
              )}
            </div>

            {/* Tags — 可点击跳转 */}
            {fm.tags.length > 0 && (
              <div style={styles.metaRow}>
                <span style={styles.metaLabel}>🏷️ 标签</span>
                <div style={styles.tagList}>
                  {fm.tags.map((tag) => (
                    <span key={tag} style={styles.tag}
                      onClick={() => handleClickLink(tag)}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Sources — 可点击 */}
            {fm.sources.length > 0 && (
              <div style={styles.metaRow}>
                <span style={styles.metaLabel}>📄 来源</span>
                <div style={styles.metaList}>
                  {fm.sources.map((s, i) => (
                    <span
                      key={i}
                      style={styles.sourceItem}
                      onClick={() => handleClickLink(s)}
                      title={s}
                    >
                      {s}
                      <span style={styles.arrow}> →</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Related — 可点击 */}
            {fm.related.length > 0 && (
              <div style={styles.metaRow}>
                <span style={styles.metaLabel}>🔗 相关</span>
                <div style={styles.metaList}>
                  {fm.related.map((rel) => (
                    <span
                      key={rel}
                      style={styles.relatedItem}
                      onClick={() => handleClickLink(rel)}
                      title={rel}
                    >
                      {rel}
                      <span style={styles.arrow}> →</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 日期 — 放在 frontmatter 最后 */}
            {(fm.created || fm.updated) && (
              <div style={styles.dateRow}>
                {fm.created && (
                  <span style={styles.dateItem}>
                    📅 创建 {new Date(fm.created).toLocaleDateString('zh-CN')}
                  </span>
                )}
                {fm.updated && (
                  <span style={styles.dateItem}>
                    ✏️ 更新 {new Date(fm.updated).toLocaleDateString('zh-CN')}
                  </span>
                )}
              </div>
            )}

            {/* 有 frontmatter 内容时才显示分割线 */}
            {(fm.type || fm.tags.length > 0 || fm.sources.length > 0 || fm.related.length > 0 || fm.created || fm.updated) && (
              <div style={styles.divider} />
            )}
          </div>
        )}

        {/* 正文 */}
        <style>{`
          .preview-markdown table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
          .preview-markdown th, .preview-markdown td { border: 1px solid ${theme.border.light}; padding: 6px 10px; text-align: left; }
          .preview-markdown th { background: ${theme.bg.header}; font-weight: 600; }
          .preview-markdown tr:nth-child(even) { background: ${theme.bg.raised}; }
          .preview-markdown code { background: ${theme.bg.raised}; padding: 1px 5px; border-radius: 3px; font-size: 12px; font-family: ${theme.fontMono}; }
          .preview-markdown pre { background: ${theme.bg.raised}; padding: 12px; border-radius: ${theme.radius.sm}; overflow-x: auto; }
          .preview-markdown pre code { background: none; padding: 0; }
          .preview-markdown blockquote { border-left: 3px solid ${theme.border.medium}; margin: 8px 0; padding: 4px 12px; color: ${theme.text.secondary}; }
        `}</style>
        <div style={styles.markdown} className="preview-markdown">
          {segments.map((seg, i) =>
            seg.type === 'text' ? (
              <ReactMarkdown
                key={i}
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt, ...props }) => {
                    // 相对路径 media/xxx → 当前项目的媒体 API
                    let imgSrc = src || '';
                    if (imgSrc.startsWith('media/') || imgSrc.startsWith('./media/')) {
                      imgSrc = `/api/projects/${encodeURIComponent(activeProjectId)}/wiki/media/${imgSrc.replace(/^\.?\/?media\//, '')}`;
                    }
                    return <img src={imgSrc} alt={alt || ''} style={{ maxWidth: '100%', borderRadius: 6, margin: '8px 0' }} {...props} />;
                  },
                }}
              >{seg.content}</ReactMarkdown>
            ) : (
              <span
                key={i}
                style={styles.wikilink}
                onClick={() => handleClickLink(seg.content)}
              >
                {seg.content}
              </span>
            ),
          )}
        </div>
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
    backgroundColor: theme.bg.content,
    borderLeft: `1px solid ${theme.border.light}`,
    fontFamily: theme.font,
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    borderBottom: `1px solid ${theme.border.light}`,
    backgroundColor: theme.bg.header,
    flexShrink: 0,
  },
  filePath: {
    fontSize: 11,
    color: theme.text.tertiary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
    fontFamily: theme.fontMono,
  },
  closeBtn: {
    border: 'none',
    background: 'none',
    fontSize: 14,
    cursor: 'pointer',
    color: theme.text.tertiary,
    padding: '2px 6px',
    borderRadius: theme.radius.sm,
    flexShrink: 0,
    lineHeight: 1,
    transition: 'all 0.15s',
  },
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px',
  },
  empty: {
    width: '100%',
    minWidth: 0,
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.bg.content,
    borderLeft: `1px solid ${theme.border.light}`,
  },
  emptyIcon: { fontSize: 28, marginBottom: 8, opacity: 0.4 },
  emptyText: { fontSize: 13, color: theme.text.tertiary },
  frontmatter: {
    marginBottom: 16,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
    flexWrap: 'wrap',
  },
  title: {
    fontSize: 17,
    fontWeight: 600,
    color: theme.text.primary,
    margin: 0,
    lineHeight: 1.3,
  },
  typeBadge: {
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 7px',
    borderRadius: 4,
    border: '1px solid',
    letterSpacing: '0.3px',
    textTransform: 'uppercase',
    flexShrink: 0,
  },
  metaRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 7,
  },
  metaLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: theme.text.secondary,
    flexShrink: 0,
    lineHeight: '20px',
    minWidth: 56,
  },
  metaList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
  },
  tagList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
  },
  tag: {
    fontSize: 11,
    padding: '1px 8px',
    borderRadius: 10,
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'opacity 0.12s',
  },
  sourceItem: {
    fontSize: 11,
    color: '#e65100',
    backgroundColor: '#fff3e0',
    padding: '1px 8px',
    borderRadius: 4,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  relatedItem: {
    fontSize: 11,
    color: '#1565c0',
    backgroundColor: '#e3f2fd',
    padding: '1px 8px',
    borderRadius: 4,
    cursor: 'pointer',
    fontWeight: 500,
    transition: 'all 0.15s',
  },
  arrow: {
    fontSize: 11,
    color: theme.text.tertiary,
  },
  dateRow: {
    display: 'flex',
    gap: 12,
    marginTop: 8,
  },
  dateItem: {
    fontSize: 11,
    color: theme.text.tertiary,
  },
  divider: {
    height: 1,
    backgroundColor: theme.border.light,
    margin: '12px 0 0',
  },
  markdown: {
    fontSize: 13,
    lineHeight: 1.65,
    color: theme.text.primary,
  },
  wikilink: {
    color: theme.accent,
    cursor: 'pointer',
    textDecoration: 'none',
    fontWeight: 500,
    borderBottom: '1px dotted',
    borderColor: theme.accent + '60',
    transition: 'border-color 0.15s',
  },
};

import { useState, useEffect, useMemo, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { fetchWikiPages, fetchWikiPage } from '../lib/api';
import { usePreview } from '../contexts/PreviewContext';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';
import type { WikiPage } from '../types';

function splitWikilinks(text: string): Array<{ type: 'text' | 'link'; content: string }> {
  const parts: Array<{ type: 'text' | 'link'; content: string }> = [];
  const regex = /\[\[([^\]]+)\]\]/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    parts.push({ type: 'link', content: match[1] });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) parts.push({ type: 'text', content: text.slice(lastIndex) });
  return parts;
}

const TYPE_LABELS: Record<string, string> = {
  entity: '实体', concept: '概念', source: '来源',
  comparison: '对比', query: '问题', synthesis: '综合',
  finding: '发现', thesis: '论点', methodology: '方法',
};

export function WikiBrowser() {
  const [pageContent, setPageContent] = useState<any>(null);
  const [allPages, setAllPages] = useState<WikiPage[]>([]);
  const [loading, setLoading] = useState(false);
  const { activePath, openPreview } = usePreview();
  const { activeProjectId } = useProject();

  useEffect(() => {
    fetchWikiPages(activeProjectId)
      .then((data) => setAllPages(data.pages || []))
      .catch(console.error);
  }, [activeProjectId]);

  const pageMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const p of allPages) {
      if (p.title) map.set(p.title, p.path);
      const nameNoExt = p.name.replace(/\.md$/, '');
      if (!map.has(nameNoExt)) map.set(nameNoExt, p.path);
    }
    return map;
  }, [allPages]);

  // activePath 变化时加载页面内容
  useEffect(() => {
    if (!activePath) return;
    setLoading(true);
    fetchWikiPage(activePath, activeProjectId)
      .then((data) => setPageContent(data))
      .catch(() => setPageContent(null))
      .finally(() => setLoading(false));
  }, [activePath]);

  const allPagesRef = useRef(allPages);
  allPagesRef.current = allPages;
  const pageMapRef = useRef(pageMap);
  pageMapRef.current = pageMap;

  const handleWikilinkClick = (target: string) => {
    const decoded = decodeURIComponent(target);
    const pages = allPagesRef.current;
    const map = pageMapRef.current;
    if (pages.some((p) => p.path === decoded)) { openPreview(decoded); return; }
    const resolved = map.get(decoded);
    if (resolved) { openPreview(resolved); return; }
    const found = pages.find((p) =>
      p.title?.includes(decoded) || p.path.includes(decoded)
    );
    if (found) openPreview(found.path);
  };

  const segments = useMemo(() => {
    if (!pageContent?.body) return [];
    return splitWikilinks(pageContent.body);
  }, [pageContent]);

  if (loading) {
    return <div style={styles.emptyContent}>加载中...</div>;
  }

  return (
    <div style={styles.container}>
      {pageContent ? (
        <>
          <div style={styles.pageHeader}>
            <h2 style={styles.pageTitle}>
              {pageContent.frontmatter?.title || activePath}
            </h2>
            {pageContent.frontmatter?.type && (
              <span style={styles.typeTag}>{TYPE_LABELS[pageContent.frontmatter.type] || pageContent.frontmatter.type}</span>
            )}
            {pageContent.frontmatter?.tags && (
              <div style={styles.tags}>
                {pageContent.frontmatter.tags.map((t: string, i: number) => (
                  <span key={i} style={styles.tag}
                    onClick={() => handleWikilinkClick(t)}
                  >{t}</span>
                ))}
              </div>
            )}
          </div>
          <div style={styles.pageBody}>
            {segments.map((seg, i) => {
              if (seg.type === 'link') {
                return (
                  <span key={i} style={styles.wikilink}
                    onClick={() => handleWikilinkClick(seg.content)}>
                    {seg.content}
                  </span>
                );
              }
              return (
                <ReactMarkdown key={i} components={{
                  code({ className, children, ...props }) {
                    const isBlock = String(children).includes('\n');
                    if (isBlock) return <pre style={styles.codeBlock}><code className={className} {...props}>{children}</code></pre>;
                    return <code style={styles.inlineCode} {...props}>{children}</code>;
                  },
                }}>
                  {seg.content}
                </ReactMarkdown>
              );
            })}
          </div>
        </>
      ) : (
        <div style={styles.emptyContent}>
          <p style={{ fontSize: 15, fontWeight: 500, color: theme.text.secondary, marginBottom: 4 }}>选择页面查看内容</p>
          <p style={{ fontSize: 13, color: theme.text.tertiary }}>点击左侧知识树中的页面</p>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, overflowY: 'auto', padding: 28, fontFamily: theme.font },
  pageHeader: { marginBottom: 24 },
  pageTitle: { fontSize: 24, fontWeight: 700, color: theme.text.primary, margin: '0 0 10px', letterSpacing: '-0.3px' },
  typeTag: {
    display: 'inline-block', padding: '2px 10px',
    backgroundColor: theme.accent, color: theme.text.inverse,
    borderRadius: 10, fontSize: 11, marginRight: 8,
  },
  tags: { display: 'flex', gap: 4, marginTop: 8 },
  tag: {
    padding: '2px 8px', backgroundColor: theme.bg.raised,
    borderRadius: 10, fontSize: 11, color: theme.text.secondary,
    cursor: 'pointer', transition: 'opacity 0.12s',
  },
  pageBody: { fontSize: 14, lineHeight: 1.75, color: theme.text.primary },
  emptyContent: {
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    color: theme.text.tertiary,
  },
  wikilink: {
    color: theme.accent, textDecoration: 'none',
    borderBottom: `1px solid ${theme.accent}40`,
    cursor: 'pointer', fontWeight: 500,
  },
  codeBlock: {
    backgroundColor: '#1e1e1e', color: '#d4d4d4',
    padding: '12px 16px', borderRadius: theme.radius.sm,
    overflowX: 'auto', fontSize: 13, lineHeight: 1.5, margin: '8px 0',
    fontFamily: theme.fontMono,
  },
  inlineCode: {
    backgroundColor: theme.bg.raised, color: '#e01e5a',
    padding: '2px 6px', borderRadius: 4, fontSize: 13,
    fontFamily: theme.fontMono,
  },
};

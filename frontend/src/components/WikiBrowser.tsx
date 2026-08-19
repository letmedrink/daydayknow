import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  deleteWikiPage, fetchWikiPage, fetchWikiPageHistory, fetchWikiPageVersion,
  fetchWikiPages, renameWikiPage, restoreWikiPageVersion, saveWikiPage,
} from '../lib/api';
import { usePreview } from '../contexts/PreviewContext';
import { useProject } from '../contexts/ProjectContext';
import { theme } from '../lib/theme';
import { wikilinksToMarkdown, wikilinkTarget } from '../lib/wikiMarkdown';
import type { WikiPage, WikiPageContent, WikiPageVersion } from '../types';

const TYPE_LABELS: Record<string, string> = {
  entity: '实体', concept: '概念', source: '来源', comparison: '对比', query: '问题',
  synthesis: '综合', finding: '发现', thesis: '论点', methodology: '方法',
};

const emptyPage = (title: string) => `---\ntitle: ${title}\ntype: concept\ntags: []\n---\n\n# ${title}\n\n`;

function simpleLineDiff(current: string, historical: string) {
  const currentLines = new Set(current.split('\n'));
  const historicalLines = new Set(historical.split('\n'));
  return [
    ...historical.split('\n').filter((line) => !currentLines.has(line)).map((line) => ({ kind: 'removed', line })),
    ...current.split('\n').filter((line) => !historicalLines.has(line)).map((line) => ({ kind: 'added', line })),
  ];
}

export function WikiBrowser() {
  const [pageContent, setPageContent] = useState<WikiPageContent | null>(null);
  const [allPages, setAllPages] = useState<WikiPage[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<WikiPageVersion[] | null>(null);
  const [historyPreview, setHistoryPreview] = useState<(WikiPageContent & { id?: string }) | null>(null);
  const { activePath, openPreview, setActivePath } = usePreview();
  const { activeProjectId } = useProject();

  const reloadPages = () => fetchWikiPages(activeProjectId).then((data) => setAllPages(data.pages || []));
  const loadPage = async (path: string) => {
    setLoading(true);
    try { setPageContent(await fetchWikiPage(path, activeProjectId)); setError(''); }
    catch (e) { setPageContent(null); setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  };
  const notifyUpdated = () => { window.dispatchEvent(new Event('wikiPagesUpdated')); void reloadPages(); };

  useEffect(() => { void reloadPages(); }, [activeProjectId]);
  useEffect(() => {
    setEditing(false); setHistory(null); setHistoryPreview(null);
    if (activePath) void loadPage(activePath);
    else setPageContent(null);
  }, [activePath, activeProjectId]);

  const pageMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const page of allPages) {
      if (page.title) map.set(page.title, page.path);
      if (!map.has(page.name)) map.set(page.name, page.path);
    }
    return map;
  }, [allPages]);

  const markdownContent = useMemo(() => wikilinksToMarkdown(pageContent?.body || ''), [pageContent]);
  const rawContent = pageContent ? `${pageContent.rawBlock || ''}${pageContent.body || ''}` : '';
  const historyRaw = historyPreview ? `${historyPreview.rawBlock || ''}${historyPreview.body || ''}` : '';
  const diffLines = useMemo(() => simpleLineDiff(rawContent, historyRaw), [rawContent, historyRaw]);

  const handleWikilinkClick = (target: string) => {
    const decoded = decodeURIComponent(target);
    const exact = allPages.find((page) => page.path === decoded)?.path || pageMap.get(decoded);
    const fuzzy = allPages.find((page) => page.title?.includes(decoded) || page.path.includes(decoded))?.path;
    if (exact || fuzzy) openPreview(exact || fuzzy!);
  };

  const beginCreate = () => {
    const title = window.prompt('新页面标题：')?.trim();
    if (!title) return;
    const proposed = `concepts/${title.replace(/[\\/:*?"<>|]/g, '-')}.md`;
    const path = window.prompt('页面路径（必须位于 Wiki 内并以 .md 结尾）：', proposed)?.trim();
    if (!path) return;
    setActivePath(path); setPageContent(null); setDraft(emptyPage(title)); setEditing(true); setError('');
  };

  const beginEdit = () => { setDraft(rawContent); setEditing(true); setError(''); };
  const save = async () => {
    if (!activePath) return;
    setSaving(true);
    try {
      const page = await saveWikiPage(activePath, draft, activeProjectId);
      setPageContent(page); setEditing(false); setError(''); notifyUpdated();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setSaving(false); }
  };

  const rename = async () => {
    if (!activePath) return;
    const nextPath = window.prompt('新页面路径：', activePath)?.trim();
    if (!nextPath || nextPath === activePath) return;
    try {
      await renameWikiPage(activePath, nextPath, activeProjectId, true);
      setActivePath(nextPath); notifyUpdated(); setError('');
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  const remove = async () => {
    if (!activePath || !window.confirm(`删除 ${activePath}？删除前会保留历史备份。`)) return;
    try {
      await deleteWikiPage(activePath, activeProjectId); setActivePath(''); setPageContent(null); notifyUpdated();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  const toggleHistory = async () => {
    if (!activePath) return;
    if (history) { setHistory(null); setHistoryPreview(null); return; }
    try { setHistory(await fetchWikiPageHistory(activePath, activeProjectId)); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  const previewVersion = async (version: WikiPageVersion) => {
    if (!activePath) return;
    try { setHistoryPreview(await fetchWikiPageVersion(activePath, version.id, activeProjectId)); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  const restoreVersion = async () => {
    if (!activePath || !historyPreview?.id || !window.confirm('恢复此版本？当前版本会先保存到历史。')) return;
    try {
      const page = await restoreWikiPageVersion(activePath, historyPreview.id, activeProjectId);
      setPageContent(page); setHistoryPreview(null); setHistory(await fetchWikiPageHistory(activePath, activeProjectId)); notifyUpdated();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  if (loading) return <div style={styles.emptyContent}>加载中...</div>;

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <button style={styles.primaryBtn} onClick={beginCreate}>新建页面</button>
        {pageContent && !editing && <button style={styles.btn} onClick={beginEdit}>编辑</button>}
        {pageContent && !editing && <button style={styles.btn} onClick={rename}>重命名</button>}
        {activePath && !editing && <button style={styles.btn} onClick={toggleHistory}>历史</button>}
        {pageContent && !editing && <button style={styles.dangerBtn} onClick={remove}>删除</button>}
        {editing && <><button style={styles.primaryBtn} onClick={save} disabled={saving}>{saving ? '保存中...' : '保存'}</button><button style={styles.btn} onClick={() => setEditing(false)}>取消</button></>}
      </div>
      {error && <div style={styles.error}>{error}</div>}

      {editing ? (
        <textarea style={styles.editor} value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} />
      ) : pageContent ? (
        <>
          <div style={styles.pageHeader}>
            <h2 style={styles.pageTitle}>{pageContent.frontmatter?.title || activePath}</h2>
            {pageContent.frontmatter?.type && <span style={styles.typeTag}>{TYPE_LABELS[pageContent.frontmatter.type] || pageContent.frontmatter.type}</span>}
            {Array.isArray(pageContent.frontmatter?.tags) && <div style={styles.tags}>{pageContent.frontmatter.tags.map((tag: string) => <span key={tag} style={styles.tag} onClick={() => handleWikilinkClick(tag)}>{tag}</span>)}</div>}
          </div>
          <div style={styles.pageBody}><ReactMarkdown components={{
            a({ href, children, ...props }) {
              const target = wikilinkTarget(href);
              return target
                ? <span style={styles.wikilink} onClick={() => handleWikilinkClick(target)}>{children}</span>
                : <a href={href} {...props}>{children}</a>;
            },
            code({ className, children, ...props }) { const block = String(children).includes('\n'); return block ? <pre style={styles.codeBlock}><code className={className} {...props}>{children}</code></pre> : <code style={styles.inlineCode} {...props}>{children}</code>; },
          }}>{markdownContent}</ReactMarkdown></div>
        </>
      ) : <div style={styles.emptyContent}><p>选择页面查看内容，或创建新页面</p></div>}

      {history && <aside style={styles.historyPanel}>
        <h3 style={styles.historyTitle}>版本历史</h3>
        {history.length === 0 ? <p style={styles.muted}>暂无历史版本</p> : history.map((version) => <button key={version.id} style={styles.versionBtn} onClick={() => previewVersion(version)}>{new Date(version.createdAt * 1000).toLocaleString()} · {version.size} B</button>)}
        {historyPreview && <div>
          <h4 style={styles.diffTitle}>与当前版本的行差异</h4>
          <pre style={styles.historyPreview}>{diffLines.length === 0 ? '无内容差异' : diffLines.map((item) => `${item.kind === 'removed' ? '- ' : '+ '}${item.line}`).join('\n')}</pre>
          <details><summary>查看历史版本全文</summary><pre style={styles.historyPreview}>{historyRaw}</pre></details>
          <button style={styles.primaryBtn} onClick={restoreVersion}>恢复此版本</button>
        </div>}
      </aside>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, overflowY: 'auto', padding: 28, fontFamily: theme.font, position: 'relative' },
  toolbar: { display: 'flex', gap: 8, marginBottom: 18, flexWrap: 'wrap' },
  btn: { padding: '7px 12px', border: `1px solid ${theme.border.medium}`, borderRadius: theme.radius.sm, background: theme.bg.raised, color: theme.text.primary, cursor: 'pointer' },
  primaryBtn: { padding: '7px 12px', border: 'none', borderRadius: theme.radius.sm, background: theme.accent, color: '#fff', cursor: 'pointer' },
  dangerBtn: { padding: '7px 12px', border: '1px solid #d9aaa6', borderRadius: theme.radius.sm, background: '#fff0ee', color: '#a23c36', cursor: 'pointer' },
  error: { padding: 10, marginBottom: 12, borderRadius: 6, background: '#f4deda', color: '#9d3e38', fontSize: 13 },
  editor: { width: '100%', minHeight: 'calc(100vh - 150px)', boxSizing: 'border-box', resize: 'vertical', padding: 16, border: `1px solid ${theme.border.medium}`, borderRadius: theme.radius.md, background: theme.bg.content, color: theme.text.primary, fontFamily: theme.fontMono, fontSize: 13, lineHeight: 1.6 },
  pageHeader: { marginBottom: 24 }, pageTitle: { fontSize: 24, fontWeight: 700, color: theme.text.primary, margin: '0 0 10px' },
  typeTag: { display: 'inline-block', padding: '2px 10px', backgroundColor: theme.accent, color: theme.text.inverse, borderRadius: 10, fontSize: 11, marginRight: 8 },
  tags: { display: 'flex', gap: 4, marginTop: 8 }, tag: { padding: '2px 8px', backgroundColor: theme.bg.raised, borderRadius: 10, fontSize: 11, color: theme.text.secondary, cursor: 'pointer' },
  pageBody: { fontSize: 14, lineHeight: 1.75, color: theme.text.primary },
  emptyContent: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.text.tertiary, minHeight: 240 },
  wikilink: { color: theme.accent, borderBottom: `1px solid ${theme.accent}40`, cursor: 'pointer', fontWeight: 500 },
  codeBlock: { backgroundColor: '#1e1e1e', color: '#d4d4d4', padding: '12px 16px', borderRadius: theme.radius.sm, overflowX: 'auto', fontSize: 13, fontFamily: theme.fontMono },
  inlineCode: { backgroundColor: theme.bg.raised, color: '#e01e5a', padding: '2px 6px', borderRadius: 4, fontSize: 13, fontFamily: theme.fontMono },
  historyPanel: { marginTop: 28, padding: 16, border: `1px solid ${theme.border.light}`, borderRadius: theme.radius.md, background: theme.bg.raised },
  historyTitle: { margin: '0 0 10px', fontSize: 15 }, muted: { color: theme.text.tertiary, fontSize: 13 },
  diffTitle: { margin: '12px 0 6px', fontSize: 13, color: theme.text.secondary },
  versionBtn: { display: 'block', width: '100%', textAlign: 'left', padding: 8, marginBottom: 5, border: `1px solid ${theme.border.light}`, borderRadius: 5, background: theme.bg.content, cursor: 'pointer', color: theme.text.secondary },
  historyPreview: { maxHeight: 320, overflow: 'auto', whiteSpace: 'pre-wrap', padding: 12, background: theme.bg.content, borderRadius: 5, fontSize: 12 },
};

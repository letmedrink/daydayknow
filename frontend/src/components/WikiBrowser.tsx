import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { fetchWikiPages, fetchWikiPage } from '../lib/api';
import type { WikiPage } from '../types';

export function WikiBrowser() {
  const [tree, setTree] = useState<WikiPage[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [pageContent, setPageContent] = useState<any>(null);

  useEffect(() => {
    fetchWikiPages().then((data) => setTree(data.tree)).catch(console.error);
  }, []);

  const handleSelect = async (path: string) => {
    setSelectedPath(path);
    try {
      const content = await fetchWikiPage(path);
      setPageContent(content);
    } catch (e) {
      setPageContent(null);
    }
  };

  const renderTree = (items: WikiPage[], depth = 0) => {
    return items.map((item) => (
      <div key={item.path}>
        <div
          style={{
            ...styles.treeItem,
            paddingLeft: 12 + depth * 16,
            ...(selectedPath === item.path ? styles.treeItemActive : {}),
          }}
          onClick={() => !item.is_dir && handleSelect(item.path)}
        >
          {item.is_dir ? '📁' : '📄'} {item.name}
        </div>
        {item.is_dir && item.children && renderTree(item.children, depth + 1)}
      </div>
    ));
  };

  return (
    <div style={styles.container}>
      <div style={styles.sidebar}>
        <h3 style={styles.sidebarTitle}>Wiki 页面</h3>
        <div style={styles.tree}>
          {tree.length === 0 ? (
            <p style={styles.empty}>暂无页面</p>
          ) : (
            renderTree(tree)
          )}
        </div>
      </div>

      <div style={styles.content}>
        {pageContent ? (
          <>
            <div style={styles.pageHeader}>
              <h2 style={styles.pageTitle}>
                {pageContent.frontmatter?.title || selectedPath}
              </h2>
              {pageContent.frontmatter?.type && (
                <span style={styles.typeTag}>{pageContent.frontmatter.type}</span>
              )}
              {pageContent.frontmatter?.tags && (
                <div style={styles.tags}>
                  {pageContent.frontmatter.tags.map((t: string, i: number) => (
                    <span key={i} style={styles.tag}>{t}</span>
                  ))}
                </div>
              )}
            </div>
            <div style={styles.pageBody}>
              <ReactMarkdown>{pageContent.body}</ReactMarkdown>
            </div>
          </>
        ) : (
          <div style={styles.emptyContent}>
            <p>选择左侧页面查看内容</p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, display: 'flex', height: '100vh' },
  sidebar: {
    width: 240,
    minWidth: 240,
    borderRight: '1px solid #d5ccc3',
    backgroundColor: '#eae3db',
    overflowY: 'auto',
  },
  sidebarTitle: {
    fontSize: 14,
    fontWeight: 700,
    color: '#4a443d',
    padding: '16px 12px 8px',
    margin: 0,
  },
  tree: { padding: '0 4px' },
  treeItem: {
    padding: '6px 8px',
    cursor: 'pointer',
    fontSize: 13,
    color: '#6b5b4f',
    borderRadius: 4,
    transition: 'background-color 0.1s',
  },
  treeItemActive: {
    backgroundColor: '#d5ccc3',
    fontWeight: 600,
  },
  empty: { padding: 12, color: '#a09890', fontSize: 13 },
  content: { flex: 1, overflowY: 'auto', padding: 24 },
  pageHeader: { marginBottom: 20 },
  pageTitle: { fontSize: 22, fontWeight: 700, color: '#4a443d', margin: '0 0 8px' },
  typeTag: {
    display: 'inline-block',
    padding: '2px 10px',
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    borderRadius: 10,
    fontSize: 11,
    marginRight: 8,
  },
  tags: { display: 'flex', gap: 4, marginTop: 8 },
  tag: {
    padding: '2px 8px',
    backgroundColor: '#d5ccc3',
    borderRadius: 10,
    fontSize: 11,
    color: '#6b5b4f',
  },
  pageBody: { fontSize: 14, lineHeight: 1.7, color: '#4a443d' },
  emptyContent: { textAlign: 'center', padding: 60, color: '#a09890' },
};

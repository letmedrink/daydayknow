import { useState, useRef, useEffect, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { GuidedOptions } from './GuidedOptions';
import { usePreview } from '../contexts/PreviewContext';
import { useProject } from '../contexts/ProjectContext';
import { fetchWikiPages } from '../lib/api';
import { theme } from '../lib/theme';
import type { Message, GuidedOption, WikiReference, Conversation, WikiPage } from '../types';

// ─── 思考过程解析 ─────────────────────────────────────────

interface ThinkingResult {
  thinking: string | null;
  answer: string;
}

function separateThinking(text: string): ThinkingResult {
  // 匹配完整的 <think>...</think> 或 <thinking>...</thinking> 块
  const closedRegex = /<think(?:ing)?>([\s\S]*?)<\/think(?:ing)?>/gi;
  const closedMatches = [...text.matchAll(closedRegex)];
  const thinking = closedMatches.map((m) => m[1].trim()).filter(Boolean).join('\n\n') || null;

  // 匹配未关闭的 <think>...（流式进行中）
  const unclosedRegex = /<think(?:ing)?>([\s\S]*)$/i;
  const unclosedMatch = text.match(unclosedRegex);

  let effectiveThinking = thinking;
  let answer = text.replace(closedRegex, '').trim();

  if (unclosedMatch && !closedMatches.some((m) => m.index! <= unclosedMatch.index!)) {
    // 有未关闭的 think 标签（流式中）
    effectiveThinking = unclosedMatch[1].trim();
    answer = text.slice(0, unclosedMatch.index).trim();
  }

  return { thinking: effectiveThinking, answer };
}

/** 流式思考块 — 仅显示最后几行，渐变透明 */
function StreamingThinkingBlock({ text }: { text: string }) {
  const lines = text.split('\n').filter(Boolean);
  const visible = lines.slice(-8);
  const lineCount = lines.length;

  return (
    <div style={styles.thinkingStreamBox}>
      <div style={styles.thinkingStreamHeader}>
        <span style={styles.thinkingDot}>●</span>
        <span>思考中</span>
        <span style={styles.thinkingLineCount}>{lineCount} 行</span>
      </div>
      <div style={styles.thinkingStreamBody}>
        {visible.map((line, i) => {
          const opacity = 0.4 + (i / Math.max(visible.length - 1, 1)) * 0.6;
          return (
            <div key={i} style={{ ...styles.thinkingLine, opacity }}>
              {line}
            </div>
          );
        })}
        <span style={styles.thinkingCursor}>▌</span>
      </div>
    </div>
  );
}

/** 完成后的思考块 — 默认展开，可折叠 */
function ThinkingBlock({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(true);
  const lineCount = text.split('\n').filter(Boolean).length;

  return (
    <div style={styles.thinkingBox}>
      <div
        style={styles.thinkingHeader}
        onClick={() => setExpanded(!expanded)}
      >
        <span style={styles.thinkingIcon}>🧠</span>
        <span>思考了 {lineCount} 行</span>
        <span style={styles.thinkingToggle}>{expanded ? '▾' : '▸'}</span>
      </div>
      {expanded && (
        <div style={styles.thinkingBody}>
          <pre style={styles.thinkingPre}>{text}</pre>
        </div>
      )}
    </div>
  );
}

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins}分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `${days}天前`;
}

/** 将文本按 [[wikilink]] 拆分为段落数组 */
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

/** 全局 wiki 页面缓存（按项目隔离） */
const _cache = new Map<string, { pages: WikiPage[] | null; promise: Promise<void> | null }>();
function _getCache(projectId: string) {
  if (!_cache.has(projectId)) _cache.set(projectId, { pages: null, promise: null });
  return _cache.get(projectId)!;
}
function ensureWikiPagesLoaded(projectId: string) {
  const c = _getCache(projectId);
  if (c.pages) return;
  if (!c.promise) {
    c.promise = fetchWikiPages(projectId)
      .then((data) => { c.pages = data.pages || []; })
      .catch(() => {});
  }
}

/** 强制刷新 wiki 页面缓存 */
export function refreshWikiPagesCache(projectId?: string) {
  const id = projectId || 'default';
  _cache.delete(id);
}

function resolveWikilinkTarget(target: string, projectId: string): string {
  const c = _getCache(projectId);
  const pages = c.pages || [];
  // 精确 path 匹配
  if (pages.some((p) => p.path === target)) return target;
  // title / name 匹配
  const byTitle = pages.find((p) => p.title === target || p.name.replace(/\.md$/, '') === target);
  if (byTitle) return byTitle.path;
  // 模糊匹配
  const fuzzy = pages.find((p) => p.title?.includes(target) || p.path.includes(target));
  return fuzzy?.path ?? target;
}

function MarkdownContent({ content, isStreaming = false, projectId = 'default' }: { content: string; isStreaming?: boolean; projectId?: string }) {
  const { openPreview } = usePreview();
  const { thinking, answer } = useMemo(() => separateThinking(content), [content]);
  const segments = useMemo(() => splitWikilinks(answer), [answer]);

  // 确保 wiki 页面列表已加载（用于 wikilink 解析）
  useEffect(() => { ensureWikiPagesLoaded(projectId); }, [projectId]);

  return (
    <div style={styles.markdownContent}>
      {/* 思考过程 */}
      {thinking && !answer && isStreaming && <StreamingThinkingBlock text={thinking} />}
      {thinking && (answer || !isStreaming) && <ThinkingBlock text={thinking} />}

      {/* 正文：分段渲染，text 段走 ReactMarkdown，link 段用 span */}
      {answer && segments.map((seg, i) => {
        if (seg.type === 'link') {
          return (
            <span
              key={i}
              style={{ ...styles.wikilink, display: 'inline', cursor: 'pointer' }}
              onClick={() => openPreview(resolveWikilinkTarget(seg.content, projectId))}
            >
              {seg.content}
            </span>
          );
        }
        return (
          <ReactMarkdown
            key={i}
            components={{
              code({ className, children, ...props }) {
                const isBlock = String(children).includes('\n');
                if (isBlock) return <pre style={styles.codeBlock}><code className={className} {...props}>{children}</code></pre>;
                return <code style={styles.inlineCode} {...props}>{children}</code>;
              },
              p({ children }) { return <span>{children}</span>; },
              ul({ children }) { return <ul style={styles.mdList}>{children}</ul>; },
              ol({ children }) { return <ol style={styles.mdList}>{children}</ol>; },
              h1({ children }) { return <h1 style={styles.mdH1}>{children}</h1>; },
              h2({ children }) { return <h2 style={styles.mdH2}>{children}</h2>; },
              h3({ children }) { return <h3 style={styles.mdH3}>{children}</h3>; },
              blockquote({ children }) { return <blockquote style={styles.mdBlockquote}>{children}</blockquote>; },
              table({ children }) { return <table style={styles.mdTable}>{children}</table>; },
              th({ children }) { return <th style={styles.mdTh}>{children}</th>; },
              td({ children }) { return <td style={styles.mdTd}>{children}</td>; },
              a({ href, children, node, ...props }) {
                return <a href={href} {...props}>{children}</a>;
              },
            }}
          >
            {seg.content}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}

interface ChatWindowProps {
  messages: Message[];
  streamingContent: string;
  isLoading: boolean;
  sendMessage: (content: string) => void;
  currentOptions: GuidedOption[];
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
}

export function ChatWindow({
  messages, streamingContent, isLoading, sendMessage,
  currentOptions,
  conversations, activeConversationId,
  onSelectConversation, onNewConversation, onDeleteConversation,
}: ChatWindowProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { openPreview } = usePreview();
  const { activeProjectId } = useProject();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  const handleOptionSelect = (opt: GuidedOption) => {
    sendMessage(opt.action);
  };

  const handleRefClick = (ref: WikiReference) => {
    openPreview(ref.path);
  };

  return (
    <div style={styles.container}>
      {/* 对话列表侧栏 */}
      <div style={styles.convPanel}>
        <div style={styles.convHeader}>
          <span style={styles.convTitle}>对话</span>
          <button style={styles.newBtn} onClick={onNewConversation}>+ 新建</button>
        </div>
        <div style={styles.convList}>
          {conversations.length === 0 && (
            <div style={styles.convEmpty}>暂无对话记录</div>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.id}
              style={{
                ...styles.convItem,
                ...(activeConversationId === conv.id ? styles.convItemActive : {}),
              }}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div style={styles.convItemTitle}>{conv.title || '新对话'}</div>
              <div style={styles.convItemMeta}>
                <span>{timeAgo(conv.updatedAt)}</span>
                <button
                  style={styles.convDeleteBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 聊天主区域 */}
      <div style={styles.chatArea}>
        <div style={styles.messagesContainer}>
          {messages.length === 0 && !streamingContent && (
            <div style={styles.emptyState}>
              <p style={{ fontSize: 16, marginBottom: 8 }}>输入任意问题开始对话</p>
              <p style={styles.hint}>AI 会基于你的知识库回答，并引导你深入学习</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                ...styles.message,
                ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage),
              }}
            >
              <div style={styles.messageRole}>
                {msg.role === 'user' ? '你' : 'llmwiki'}
              </div>
              <div style={styles.messageContent}>
                {msg.role === 'user' ? msg.content : <MarkdownContent content={msg.content} projectId={activeProjectId} />}
              </div>
              {msg.role === 'assistant' && msg.references && msg.references.length > 0 && (
                <div style={styles.references}>
                  参考: {msg.references.map((ref, ri) => (
                    <span
                      key={ri}
                      style={{ ...styles.refTag, ...styles.refTagClickable }}
                      onClick={() => handleRefClick(ref)}
                    >
                      {ref.title}
                    </span>
                  ))}
                </div>
              )}
              {msg.role === 'assistant' && msg.options && msg.options.length > 0 && i === messages.length - 1 && !streamingContent && (
                <GuidedOptions options={msg.options} onSelect={handleOptionSelect} disabled={isLoading} />
              )}
            </div>
          ))}

          {streamingContent && (
            <div style={{ ...styles.message, ...styles.assistantMessage }}>
              <div style={styles.messageRole}>llmwiki</div>
              <div style={styles.messageContent}>
                <MarkdownContent content={streamingContent} isStreaming={true} projectId={activeProjectId} />
                <span style={styles.cursor}>|</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {!streamingContent && currentOptions.length > 0 && messages.length > 0 && !isLoading && (
          <div style={styles.optionsBar}>
            <GuidedOptions options={currentOptions} onSelect={handleOptionSelect} disabled={isLoading} />
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.inputArea}>
          <input
            style={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入你的问题..."
            disabled={isLoading}
          />
          <button
            type="submit"
            style={styles.sendButton}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? '生成中...' : '发送'}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1, display: 'flex', height: '100%',
    backgroundColor: theme.bg.content, minWidth: 0,
    fontFamily: theme.font,
  },
  // ─── 对话列表 ─────────────────────────────
  convPanel: {
    width: 220, minWidth: 220,
    backgroundColor: theme.bg.sidebar,
    borderRight: `1px solid ${theme.border.light}`,
    display: 'flex', flexDirection: 'column',
  },
  convHeader: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', padding: '12px 12px 8px',
  },
  convTitle: { fontSize: 11, fontWeight: 600, color: theme.text.secondary, textTransform: 'uppercase', letterSpacing: '0.5px' },
  newBtn: {
    padding: '3px 10px', backgroundColor: theme.accent,
    color: theme.text.inverse, border: 'none',
    borderRadius: theme.radius.sm, fontSize: 12,
    fontWeight: 600, cursor: 'pointer', fontFamily: theme.font,
  },
  convList: { flex: 1, overflowY: 'auto', padding: '0 6px 6px' },
  convEmpty: { textAlign: 'center', padding: '20px', color: theme.text.tertiary, fontSize: 13 },
  convItem: {
    padding: '8px 10px', borderRadius: theme.radius.sm,
    cursor: 'pointer', marginBottom: 1, transition: 'background-color 0.1s',
  },
  convItemActive: { backgroundColor: theme.bg.overlay },
  convItemTitle: {
    fontSize: 13, fontWeight: 500, color: theme.text.primary,
    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 2,
  },
  convItemMeta: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: theme.text.tertiary },
  convDeleteBtn: {
    marginLeft: 'auto', background: 'none', border: 'none',
    color: theme.text.tertiary, fontSize: 14, cursor: 'pointer',
    padding: '0 4px', lineHeight: 1,
  },
  // ─── 聊天主区域 ───────────────────────────
  chatArea: { flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 },
  messagesContainer: {
    flex: 1, overflowY: 'auto', padding: '20px 24px',
    maxWidth: 720, width: '100%', margin: '0 auto', boxSizing: 'border-box',
  },
  emptyState: { textAlign: 'center', padding: '80px 20px', color: theme.text.tertiary },
  hint: { fontSize: 13, marginTop: 8 },
  message: { marginBottom: 16, padding: '12px 16px', borderRadius: theme.radius.lg, maxWidth: '85%' },
  userMessage: { backgroundColor: theme.accent, color: theme.text.inverse, marginLeft: 'auto' },
  assistantMessage: { backgroundColor: theme.bg.raised, color: theme.text.primary, border: `1px solid ${theme.border.light}` },
  messageRole: { fontSize: 11, fontWeight: 600, marginBottom: 4, opacity: 0.6 },
  messageContent: { fontSize: 14, lineHeight: 1.65 },
  references: {
    display: 'flex', flexWrap: 'wrap', gap: 4,
    marginTop: 8, paddingTop: 8,
    borderTop: `1px solid ${theme.border.light}`, fontSize: 12, color: theme.text.secondary,
  },
  refTag: {
    padding: '2px 8px', backgroundColor: theme.bg.raised,
    borderRadius: 10, fontSize: 11, color: theme.text.secondary,
    border: `1px solid ${theme.border.light}`,
  },
  refTagClickable: { cursor: 'pointer', transition: 'all 0.12s' },
  optionsBar: { padding: '4px 24px 8px', maxWidth: 720, margin: '0 auto', width: '100%', boxSizing: 'border-box' },
  refsBar: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '4px 24px', maxWidth: 720,
    margin: '0 auto', width: '100%', boxSizing: 'border-box',
    fontSize: 12, color: theme.text.secondary,
  },
  refsLabel: { fontSize: 12, color: theme.text.tertiary },
  inputArea: {
    display: 'flex', gap: 8, padding: '12px 24px',
    borderTop: `1px solid ${theme.border.light}`, backgroundColor: theme.bg.header,
  },
  input: {
    flex: 1, padding: '10px 14px',
    border: `1px solid ${theme.border.medium}`, borderRadius: theme.radius.md,
    fontSize: 14, outline: 'none',
    backgroundColor: theme.bg.content, color: theme.text.primary,
    fontFamily: theme.font, transition: 'border-color 0.15s',
  },
  sendButton: {
    padding: '10px 20px', backgroundColor: theme.accent,
    color: theme.text.inverse, border: 'none', borderRadius: theme.radius.md,
    fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: theme.font,
  },
  cursor: { animation: 'blink 1s infinite', fontWeight: 300 },
  markdownContent: {},
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
  mdP: { margin: '4px 0' },
  mdList: { margin: '4px 0', paddingLeft: 20 },
  mdH1: { fontSize: 18, fontWeight: 700, margin: '12px 0 6px', color: theme.text.primary },
  mdH2: { fontSize: 16, fontWeight: 700, margin: '10px 0 4px', color: theme.text.primary },
  mdH3: { fontSize: 15, fontWeight: 600, margin: '8px 0 4px', color: theme.text.primary },
  mdBlockquote: {
    borderLeft: `3px solid ${theme.border.medium}`, paddingLeft: 12,
    margin: '8px 0', color: theme.text.secondary,
  },
  mdTable: { borderCollapse: 'collapse', margin: '8px 0', fontSize: 13 },
  mdTh: {
    border: `1px solid ${theme.border.light}`, padding: '6px 10px',
    backgroundColor: theme.bg.raised, fontWeight: 600, textAlign: 'left',
  },
  mdTd: { border: `1px solid ${theme.border.light}`, padding: '6px 10px' },
  wikilink: {
    color: theme.accent, textDecoration: 'none',
    borderBottom: `1px solid ${theme.accent}40`,
    cursor: 'pointer', fontWeight: 500,
  },
  // ─── 思考过程样式 ─────────────────────────
  thinkingStreamBox: {
    border: `1px dashed #d4a017`,
    borderRadius: theme.radius.md,
    padding: '8px 12px',
    marginBottom: 10,
    backgroundColor: '#fffbf0',
    maxHeight: 140,
    overflow: 'hidden',
  },
  thinkingStreamHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    fontWeight: 600,
    color: '#b8860b',
    marginBottom: 6,
  },
  thinkingDot: {
    fontSize: 8,
    color: '#d4a017',
    animation: 'blink 1s infinite',
  },
  thinkingLineCount: {
    marginLeft: 'auto',
    fontWeight: 400,
    color: '#c5a55a',
  },
  thinkingStreamBody: {
    fontSize: 12,
    lineHeight: 1.5,
    color: '#8b7355',
    fontFamily: theme.fontMono,
  },
  thinkingLine: {
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  thinkingCursor: {
    color: '#d4a017',
    animation: 'blink 1s infinite',
    fontWeight: 300,
  },
  thinkingBox: {
    border: `1px solid #e0d5b8`,
    borderRadius: theme.radius.md,
    marginBottom: 10,
    backgroundColor: '#faf8f2',
    overflow: 'hidden',
  },
  thinkingHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 12px',
    fontSize: 12,
    fontWeight: 500,
    color: '#8b7355',
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  thinkingIcon: { fontSize: 14 },
  thinkingToggle: {
    marginLeft: 'auto',
    fontSize: 11,
    color: '#b8a88a',
  },
  thinkingBody: {
    maxHeight: 256,
    overflowY: 'auto',
    borderTop: `1px solid #e0d5b8`,
  },
  thinkingPre: {
    margin: 0,
    padding: '10px 12px',
    fontSize: 12,
    lineHeight: 1.5,
    fontFamily: theme.fontMono,
    color: '#6b5b4f',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  },
};

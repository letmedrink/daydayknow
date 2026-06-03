import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { GuidedOptions } from './GuidedOptions';
import type { Message, GuidedOption, WikiReference } from '../types';

function MarkdownContent({ content }: { content: string }) {
  return (
    <div style={styles.markdownContent}>
      <ReactMarkdown
        components={{
          code({ className, children, ...props }) {
            const isBlock = String(children).includes('\n');
            if (isBlock) {
              return (
                <pre style={styles.codeBlock}>
                  <code className={className} {...props}>{children}</code>
                </pre>
              );
            }
            return <code style={styles.inlineCode} {...props}>{children}</code>;
          },
          p({ children }) { return <p style={styles.mdP}>{children}</p>; },
          ul({ children }) { return <ul style={styles.mdList}>{children}</ul>; },
          ol({ children }) { return <ol style={styles.mdList}>{children}</ol>; },
          h1({ children }) { return <h1 style={styles.mdH1}>{children}</h1>; },
          h2({ children }) { return <h2 style={styles.mdH2}>{children}</h2>; },
          h3({ children }) { return <h3 style={styles.mdH3}>{children}</h3>; },
          blockquote({ children }) { return <blockquote style={styles.mdBlockquote}>{children}</blockquote>; },
          table({ children }) { return <table style={styles.mdTable}>{children}</table>; },
          th({ children }) { return <th style={styles.mdTh}>{children}</th>; },
          td({ children }) { return <td style={styles.mdTd}>{children}</td>; },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

interface ChatWindowProps {
  messages: Message[];
  streamingContent: string;
  isLoading: boolean;
  sendMessage: (content: string) => void;
  currentOptions: GuidedOption[];
  currentReferences: WikiReference[];
}

export function ChatWindow({
  messages, streamingContent, isLoading, sendMessage,
  currentOptions, currentReferences,
}: ChatWindowProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>知微</h1>
        <p style={styles.subtitle}>格物致知，见微知著</p>
      </div>

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
              {msg.role === 'user' ? '你' : '知微'}
            </div>
            <div style={styles.messageContent}>
              {msg.role === 'user' ? msg.content : <MarkdownContent content={msg.content} />}
            </div>
            {/* 引用的 wiki 页面 */}
            {msg.role === 'assistant' && msg.references && msg.references.length > 0 && (
              <div style={styles.references}>
                参考: {msg.references.map((ref, ri) => (
                  <span key={ri} style={styles.refTag}>{ref.title}</span>
                ))}
              </div>
            )}
            {/* 引导选项 */}
            {msg.role === 'assistant' && msg.options && msg.options.length > 0 && i === messages.length - 1 && !streamingContent && (
              <GuidedOptions options={msg.options} onSelect={handleOptionSelect} disabled={isLoading} />
            )}
          </div>
        ))}

        {streamingContent && (
          <div style={{ ...styles.message, ...styles.assistantMessage }}>
            <div style={styles.messageRole}>知微</div>
            <div style={styles.messageContent}>
              <MarkdownContent content={streamingContent} />
              <span style={styles.cursor}>|</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 流式结束后的引导选项 */}
      {!streamingContent && currentOptions.length > 0 && messages.length > 0 && !isLoading && (
        <div style={styles.optionsBar}>
          <GuidedOptions options={currentOptions} onSelect={handleOptionSelect} disabled={isLoading} />
        </div>
      )}

      {/* 引用面板 */}
      {currentReferences.length > 0 && !streamingContent && (
        <div style={styles.refsBar}>
          <span style={styles.refsLabel}>引用知识:</span>
          {currentReferences.map((ref, i) => (
            <span key={i} style={styles.refTag}>{ref.title}</span>
          ))}
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
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#f5f0eb',
    minWidth: 0,
  },
  header: {
    padding: '16px 20px',
    borderBottom: '1px solid #d5ccc3',
    backgroundColor: '#eae3db',
  },
  title: { fontSize: 20, fontWeight: 700, color: '#4a443d', margin: 0 },
  subtitle: { fontSize: 13, color: '#8a8078', margin: '4px 0 0' },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px',
    maxWidth: 700,
    width: '100%',
    margin: '0 auto',
    boxSizing: 'border-box',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#a09890',
  },
  hint: { fontSize: 13, marginTop: 8 },
  message: {
    marginBottom: 16,
    padding: '12px 16px',
    borderRadius: 12,
    maxWidth: '85%',
  },
  userMessage: {
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    marginLeft: 'auto',
  },
  assistantMessage: {
    backgroundColor: '#eae3db',
    color: '#4a443d',
    border: '1px solid #d5ccc3',
  },
  messageRole: { fontSize: 11, fontWeight: 600, marginBottom: 4, opacity: 0.7 },
  messageContent: { fontSize: 14, lineHeight: 1.6 },
  references: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 8,
    paddingTop: 8,
    borderTop: '1px solid #d5ccc3',
    fontSize: 12,
    color: '#8a8078',
  },
  refTag: {
    padding: '2px 8px',
    backgroundColor: '#d5ccc3',
    borderRadius: 10,
    fontSize: 11,
    color: '#6b5b4f',
  },
  optionsBar: {
    padding: '4px 20px 8px',
    maxWidth: 700,
    margin: '0 auto',
    width: '100%',
    boxSizing: 'border-box',
  },
  refsBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 20px',
    maxWidth: 700,
    margin: '0 auto',
    width: '100%',
    boxSizing: 'border-box',
    fontSize: 12,
    color: '#8a8078',
  },
  refsLabel: { fontSize: 12, color: '#a09890' },
  inputArea: {
    display: 'flex',
    gap: 8,
    padding: '12px 20px',
    borderTop: '1px solid #d5ccc3',
    backgroundColor: '#eae3db',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    border: '1px solid #c8bfb5',
    borderRadius: 8,
    fontSize: 14,
    outline: 'none',
    backgroundColor: '#f5f0eb',
    color: '#4a443d',
  },
  sendButton: {
    padding: '10px 20px',
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
  cursor: { animation: 'blink 1s infinite', fontWeight: 300 },
  markdownContent: {},
  codeBlock: {
    backgroundColor: '#4a443d',
    color: '#e8e0d8',
    padding: '12px 16px',
    borderRadius: 8,
    overflowX: 'auto',
    fontSize: 13,
    lineHeight: 1.5,
    margin: '8px 0',
  },
  inlineCode: {
    backgroundColor: '#e0d8ce',
    color: '#8b6b5e',
    padding: '2px 6px',
    borderRadius: 4,
    fontSize: 13,
  },
  mdP: { margin: '4px 0' },
  mdList: { margin: '4px 0', paddingLeft: 20 },
  mdH1: { fontSize: 18, fontWeight: 700, margin: '12px 0 6px' },
  mdH2: { fontSize: 16, fontWeight: 700, margin: '10px 0 4px' },
  mdH3: { fontSize: 15, fontWeight: 600, margin: '8px 0 4px' },
  mdBlockquote: {
    borderLeft: '3px solid #a09890',
    paddingLeft: 12,
    margin: '8px 0',
    color: '#8a8078',
  },
  mdTable: { borderCollapse: 'collapse', margin: '8px 0', fontSize: 13 },
  mdTh: {
    border: '1px solid #d5ccc3',
    padding: '6px 10px',
    backgroundColor: '#e0d8ce',
    fontWeight: 600,
    textAlign: 'left',
  },
  mdTd: { border: '1px solid #d5ccc3', padding: '6px 10px' },
};

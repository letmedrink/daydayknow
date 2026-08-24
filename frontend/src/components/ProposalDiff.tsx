import { theme } from '../lib/theme';

type DiffKind = 'context' | 'added' | 'removed';
type DiffLine = { kind: DiffKind; text: string; oldNumber: number | null; newNumber: number | null };
type Hunk = { lines: DiffLine[]; oldStart: number; oldCount: number; newStart: number; newCount: number };

const CONTEXT_LINES = 3;
const MAX_LCS_CELLS = 4_000_000;

function coarseDiff(oldLines: string[], newLines: string[]): DiffLine[] {
  let prefix = 0;
  while (prefix < oldLines.length && prefix < newLines.length && oldLines[prefix] === newLines[prefix]) prefix += 1;
  let suffix = 0;
  while (suffix < oldLines.length - prefix && suffix < newLines.length - prefix
    && oldLines[oldLines.length - 1 - suffix] === newLines[newLines.length - 1 - suffix]) suffix += 1;
  return [
    ...oldLines.slice(0, prefix).map((text, index) => ({ kind: 'context' as const, text, oldNumber: index + 1, newNumber: index + 1 })),
    ...oldLines.slice(prefix, oldLines.length - suffix).map((text, index) => ({ kind: 'removed' as const, text, oldNumber: prefix + index + 1, newNumber: null })),
    ...newLines.slice(prefix, newLines.length - suffix).map((text, index) => ({ kind: 'added' as const, text, oldNumber: null, newNumber: prefix + index + 1 })),
    ...oldLines.slice(oldLines.length - suffix).map((text, index) => ({
      kind: 'context' as const, text,
      oldNumber: oldLines.length - suffix + index + 1,
      newNumber: newLines.length - suffix + index + 1,
    })),
  ];
}

function lineDiff(before: string, after: string): DiffLine[] {
  const oldLines = before.split('\n');
  const newLines = after.split('\n');
  if (oldLines.length * newLines.length > MAX_LCS_CELLS) return coarseDiff(oldLines, newLines);

  const lcs = Array.from({ length: oldLines.length + 1 }, () => new Uint32Array(newLines.length + 1));
  for (let oldIndex = oldLines.length - 1; oldIndex >= 0; oldIndex -= 1) {
    for (let newIndex = newLines.length - 1; newIndex >= 0; newIndex -= 1) {
      lcs[oldIndex][newIndex] = oldLines[oldIndex] === newLines[newIndex]
        ? lcs[oldIndex + 1][newIndex + 1] + 1
        : Math.max(lcs[oldIndex + 1][newIndex], lcs[oldIndex][newIndex + 1]);
    }
  }

  const result: DiffLine[] = [];
  let oldIndex = 0;
  let newIndex = 0;
  while (oldIndex < oldLines.length || newIndex < newLines.length) {
    if (oldIndex < oldLines.length && newIndex < newLines.length && oldLines[oldIndex] === newLines[newIndex]) {
      result.push({ kind: 'context', text: oldLines[oldIndex], oldNumber: oldIndex + 1, newNumber: newIndex + 1 });
      oldIndex += 1; newIndex += 1;
    } else if (oldIndex < oldLines.length && (newIndex >= newLines.length || lcs[oldIndex + 1][newIndex] >= lcs[oldIndex][newIndex + 1])) {
      result.push({ kind: 'removed', text: oldLines[oldIndex], oldNumber: oldIndex + 1, newNumber: null });
      oldIndex += 1;
    } else {
      result.push({ kind: 'added', text: newLines[newIndex], oldNumber: null, newNumber: newIndex + 1 });
      newIndex += 1;
    }
  }
  return result;
}

function makeHunks(lines: DiffLine[]): Hunk[] {
  const changes = lines.flatMap((line, index) => line.kind === 'context' ? [] : [index]);
  if (!changes.length) return [];
  const ranges: Array<[number, number]> = [];
  for (const index of changes) {
    const start = Math.max(0, index - CONTEXT_LINES);
    const end = Math.min(lines.length - 1, index + CONTEXT_LINES);
    const previous = ranges[ranges.length - 1];
    if (previous && start <= previous[1] + 1) previous[1] = Math.max(previous[1], end);
    else ranges.push([start, end]);
  }
  return ranges.map(([start, end]) => {
    const selected = lines.slice(start, end + 1);
    return {
      lines: selected,
      oldStart: lines.slice(0, start).filter((line) => line.kind !== 'added').length + 1,
      newStart: lines.slice(0, start).filter((line) => line.kind !== 'removed').length + 1,
      oldCount: selected.filter((line) => line.kind !== 'added').length,
      newCount: selected.filter((line) => line.kind !== 'removed').length,
    };
  });
}

export function ProposalDiff({ before, after }: { before: string; after: string }) {
  const lines = lineDiff(before, after);
  const hunks = makeHunks(lines);
  const added = lines.filter((line) => line.kind === 'added').length;
  const removed = lines.filter((line) => line.kind === 'removed').length;

  return <details open style={styles.box}>
    <summary style={styles.summary}>Git 风格差异 <span style={styles.addedCount}>+{added}</span> <span style={styles.removedCount}>−{removed}</span></summary>
    {!hunks.length ? <div style={styles.empty}>内容没有变化</div> : <div style={styles.code}>
      <div style={styles.fileHeader}>--- 旧版本</div>
      <div style={styles.fileHeader}>+++ 提案版本</div>
      {hunks.map((hunk, hunkIndex) => <div key={hunkIndex}>
        <div style={styles.hunk}>@@ -{hunk.oldStart},{hunk.oldCount} +{hunk.newStart},{hunk.newCount} @@</div>
        {hunk.lines.map((line, lineIndex) => <div key={lineIndex} style={{ ...styles.line, ...styles[line.kind] }}>
          <span style={styles.lineNumber}>{line.oldNumber ?? ''}</span>
          <span style={styles.lineNumber}>{line.newNumber ?? ''}</span>
          <span style={styles.marker}>{line.kind === 'added' ? '+' : line.kind === 'removed' ? '−' : ' '}</span>
          <span style={styles.text}>{line.text || ' '}</span>
        </div>)}
      </div>)}
    </div>}
  </details>;
}

const styles: Record<string, React.CSSProperties> = {
  box: { marginTop: 10, color: theme.text.secondary, fontSize: 12 },
  summary: { cursor: 'pointer', fontWeight: 600, userSelect: 'none' },
  addedCount: { marginLeft: 8, color: '#16784a' },
  removedCount: { marginLeft: 5, color: '#b42318' },
  empty: { padding: 10, color: theme.text.tertiary },
  code: { maxHeight: 420, overflow: 'auto', marginTop: 8, border: `1px solid ${theme.border.light}`, borderRadius: 5, background: theme.bg.content, fontFamily: theme.fontMono, fontSize: 11, lineHeight: 1.55 },
  fileHeader: { minWidth: 'max-content', padding: '2px 10px', color: theme.text.secondary, fontWeight: 600 },
  hunk: { minWidth: 'max-content', padding: '3px 10px', color: '#315f8c', background: '#eaf3fb' },
  line: { display: 'grid', gridTemplateColumns: '48px 48px 20px minmax(max-content, 1fr)', minWidth: 'max-content' },
  lineNumber: { padding: '0 7px', textAlign: 'right', color: theme.text.tertiary, borderRight: `1px solid ${theme.border.light}`, userSelect: 'none' },
  marker: { paddingLeft: 6, userSelect: 'none' },
  text: { paddingRight: 12, whiteSpace: 'pre' },
  context: { background: theme.bg.content },
  removed: { background: '#ffebe9', color: '#7d201b' },
  added: { background: '#dafbe1', color: '#175c36' },
};

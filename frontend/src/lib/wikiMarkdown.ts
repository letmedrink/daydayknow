const WIKILINK_PREFIX = '#wikilink-';

/** Convert Obsidian-style WikiLinks into ordinary Markdown links before parsing. */
export function wikilinksToMarkdown(markdown: string): string {
  return markdown.replace(/\[\[([^\]]+)\]\]/g, (_match, rawTarget: string) => {
    const target = rawTarget.trim();
    const label = target.replace(/([\\\[\]])/g, '\\$1');
    return `[${label}](${WIKILINK_PREFIX}${encodeURIComponent(target)})`;
  });
}

export function wikilinkTarget(href?: string): string | null {
  if (!href?.startsWith(WIKILINK_PREFIX)) return null;
  try {
    return decodeURIComponent(href.slice(WIKILINK_PREFIX.length));
  } catch {
    return href.slice(WIKILINK_PREFIX.length);
  }
}

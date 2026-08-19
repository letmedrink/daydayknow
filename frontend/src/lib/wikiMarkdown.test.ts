import { describe, expect, it } from 'vitest';

import { wikilinksToMarkdown, wikilinkTarget } from './wikiMarkdown';

describe('WikiLink markdown conversion', () => {
  it('keeps surrounding prose in a single Markdown document', () => {
    expect(wikilinksToMarkdown('前文[[三界]]后文')).toBe('前文[三界](#wikilink-%E4%B8%89%E7%95%8C)后文');
  });

  it('decodes the target and ignores ordinary links', () => {
    expect(wikilinkTarget('#wikilink-%E9%9F%A9%E7%AB%8B')).toBe('韩立');
    expect(wikilinkTarget('https://example.com')).toBeNull();
  });
});

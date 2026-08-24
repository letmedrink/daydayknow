// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { ProposalDiff } from './ProposalDiff';

afterEach(cleanup);

describe('ProposalDiff', () => {
  it('renders git-style hunks with line numbers and change counts', () => {
    render(<ProposalDiff before={'alpha\nold claim\nomega'} after={'alpha\nnew claim\nomega'} />);
    expect(screen.getByText('@@ -1,3 +1,3 @@')).toBeInTheDocument();
    expect(screen.getByText('+1')).toBeInTheDocument();
    expect(screen.getByText('−1')).toBeInTheDocument();
    expect(screen.getByText('old claim')).toBeInTheDocument();
    expect(screen.getByText('new claim')).toBeInTheDocument();
  });

  it('splits distant edits into separate context hunks', () => {
    const before = Array.from({ length: 12 }, (_, index) => `line ${index}`).join('\n');
    const after = before.replace('line 1', 'changed 1').replace('line 10', 'changed 10');
    render(<ProposalDiff before={before} after={after} />);
    expect(screen.getAllByText(/^@@ /)).toHaveLength(2);
  });
});

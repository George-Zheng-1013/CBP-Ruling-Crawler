import { describe, expect, it } from 'vitest';

import { buildDecisionTreeLayout } from './ClassificationTreeView';
import type { ClassificationTree, ClassificationTreeNode } from '../types/classification';

function node(
  id: string,
  nodeType: ClassificationTreeNode['nodeType'],
  children: ClassificationTreeNode[] = [],
  evidenceIds: string[] = [],
): ClassificationTreeNode {
  return {
    id,
    nodeType,
    status: id.includes('excluded') ? 'excluded' : 'selected',
    title: id,
    htsCode: '',
    rationale: [],
    missingInformation: [],
    evidenceIds,
    children,
  };
}

describe('buildDecisionTreeLayout', () => {
  it('creates rule and heading stages while moving case nodes into heading evidence', () => {
    const selected = node('heading-selected', 'candidate_heading', [
      node('six-digit', 'subheading'),
      node('case-one', 'case', [], ['case:N1']),
    ], ['hts:8544']);
    const excluded = node('heading-excluded', 'candidate_heading', [
      node('case-two', 'case', [], ['case:N2']),
    ]);
    const tree: ClassificationTree = {
      root: node('product', 'product_facts', [
        node('gri-1', 'interpretation_rule'),
        node('chapter-note', 'legal_note'),
        selected,
        excluded,
      ]),
      evidence: [],
    };

    const layout = buildDecisionTreeLayout(tree);

    expect(layout.rules.map((item) => item.id)).toEqual(['gri-1', 'chapter-note']);
    expect(layout.headings).toHaveLength(2);
    expect(layout.headings[0].children.map((item) => item.id)).toEqual(['six-digit']);
    expect(layout.headings[0].evidenceIds).toEqual(['hts:8544', 'case:N1']);
    expect(layout.headings[1].children).toEqual([]);
  });
});

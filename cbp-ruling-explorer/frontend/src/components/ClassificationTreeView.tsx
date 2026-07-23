import { Link } from 'react-router-dom';

import type {
  ClassificationEvidence,
  ClassificationTree,
  ClassificationTreeNode,
} from '../types/classification';

const statusLabel = {
  selected: '选中',
  excluded: '排除',
  pending: '待确认',
};

const nodeLabel: Record<ClassificationTreeNode['nodeType'], string> = {
  product_facts: '商品事实',
  interpretation_rule: '解释规则',
  legal_note: '法律注释',
  candidate_heading: '候选四位品目',
  subheading: '子目路径',
  case: '参考案例',
};

function EvidenceItem({ item }: { item: ClassificationEvidence }) {
  const title = item.page ? `${item.title}（第 ${item.page} 页）` : item.title;
  return (
    <li className="classification-evidence">
      <div className="flex flex-wrap items-center gap-2">
        {item.type === 'cbp_case' && item.rulingNo ? (
          <Link className="text-blue hover:underline mono" to={`/ruling/${item.rulingNo}`}>
            {item.rulingNo}
          </Link>
        ) : item.url ? (
          <a className="text-blue hover:underline" href={item.url} target="_blank" rel="noreferrer">
            {title}
          </a>
        ) : (
          <span className="font-medium">{title}</span>
        )}
        {item.status && <span className="chip">{item.status}</span>}
      </div>
      {item.excerpt && (
        <blockquote className="mt-2 whitespace-pre-wrap text-gray-600 border-l-2 border-gray-200 pl-3">
          {item.excerpt}
        </blockquote>
      )}
    </li>
  );
}

function TreeNode({
  node,
  evidence,
  depth,
}: {
  node: ClassificationTreeNode;
  evidence: Map<string, ClassificationEvidence>;
  depth: number;
}) {
  const items = node.evidenceIds
    .map((id) => evidence.get(id))
    .filter((item): item is ClassificationEvidence => Boolean(item));
  return (
    <li className={`classification-tree-node classification-tree-node--${node.status}`}>
      <details open={depth < 2 || node.status === 'selected'}>
        <summary>
          <span className="classification-node-kind">{nodeLabel[node.nodeType]}</span>
          {node.htsCode && <span className="mono font-semibold">{node.htsCode}</span>}
          <span className="font-medium">{node.title}</span>
          <span className={`classification-node-status classification-node-status--${node.status}`}>
            {statusLabel[node.status]}
          </span>
        </summary>
        <div className="classification-node-detail">
          {node.rationale.length > 0 && (
            <ul className="list-disc pl-5 space-y-1">
              {node.rationale.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
            </ul>
          )}
          {node.missingInformation.length > 0 && (
            <div className="mt-3 text-amber-800">
              <b>待补充：</b>{node.missingInformation.join('；')}
            </div>
          )}
          {items.length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm text-blue">查看逐条证据（{items.length}）</summary>
              <ul className="mt-2 space-y-3">
                {items.map((item) => <EvidenceItem key={item.id} item={item} />)}
              </ul>
            </details>
          )}
        </div>
        {node.children.length > 0 && (
          <ul className={depth === 0 ? 'classification-tree-branches' : 'classification-tree-children'}>
            {node.children.map((child) => (
              <TreeNode key={child.id} node={child} evidence={evidence} depth={depth + 1} />
            ))}
          </ul>
        )}
      </details>
    </li>
  );
}

export function ClassificationTreeView({ tree }: { tree: ClassificationTree }) {
  const evidence = new Map(tree.evidence.map((item) => [item.id, item]));
  return (
    <section className="card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="heading">分类思路树</h2>
          <p className="caption mt-1">以法律规则为主线，案例作为类比证据；点击节点可查看依据。</p>
        </div>
        <div className="flex gap-2 text-xs" aria-label="节点状态图例">
          <span className="classification-node-status classification-node-status--selected">选中</span>
          <span className="classification-node-status classification-node-status--excluded">排除</span>
          <span className="classification-node-status classification-node-status--pending">待确认</span>
        </div>
      </div>
      <ul className="classification-tree mt-5">
        <TreeNode node={tree.root} evidence={evidence} depth={0} />
      </ul>
    </section>
  );
}

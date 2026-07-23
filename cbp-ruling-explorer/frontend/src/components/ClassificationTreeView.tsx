import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import type {
  ClassificationEvidence,
  ClassificationTree,
  ClassificationTreeNode,
} from '../types/classification';

const statusLabel = { selected: '选中', excluded: '排除', pending: '待确认' };
const nodeLabel: Record<ClassificationTreeNode['nodeType'], string> = {
  product_facts: '商品事实',
  interpretation_rule: '解释规则',
  legal_note: '法律注释',
  candidate_heading: '候选四位品目',
  subheading: '子目',
  case: '参考案例',
};

export interface DecisionTreeLayout {
  root: ClassificationTreeNode;
  rules: ClassificationTreeNode[];
  headings: ClassificationTreeNode[];
}

export function buildDecisionTreeLayout(tree: ClassificationTree): DecisionTreeLayout {
  return {
    root: tree.root,
    rules: tree.root.children.filter(
      (node) => node.nodeType === 'interpretation_rule' || node.nodeType === 'legal_note',
    ),
    headings: tree.root.children
      .filter((node) => node.nodeType === 'candidate_heading')
      .map((node) => ({
        ...node,
        evidenceIds: [
          ...node.evidenceIds,
          ...node.children
            .filter((child) => child.nodeType === 'case')
            .flatMap((child) => child.evidenceIds),
        ],
        children: node.children.filter((child) => child.nodeType === 'subheading'),
      })),
  };
}

function NodeButton({
  node,
  onOpen,
}: {
  node: ClassificationTreeNode;
  onOpen: (node: ClassificationTreeNode) => void;
}) {
  return (
    <button
      type="button"
      className={`decision-node decision-node--${node.status}`}
      onClick={() => onOpen(node)}
    >
      <span className="decision-node-kind">{nodeLabel[node.nodeType]}</span>
      <span className="decision-node-title">
        {node.htsCode && <span className="mono">{node.htsCode}</span>}
        {node.title}
      </span>
      <span className={`classification-node-status classification-node-status--${node.status}`}>
        {statusLabel[node.status]}
      </span>
    </button>
  );
}

function Path({
  node,
  onOpen,
}: {
  node: ClassificationTreeNode;
  onOpen: (node: ClassificationTreeNode) => void;
}) {
  const children = node.children.filter((child) => child.nodeType === 'subheading');
  return (
    <>
      <NodeButton node={node} onOpen={onOpen} />
      {children.map((child) => (
        <div className="decision-path-next" key={child.id}>
          <span className="decision-arrow" aria-hidden="true" />
          <Path node={child} onOpen={onOpen} />
        </div>
      ))}
    </>
  );
}

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

function EvidenceDrawer({
  node,
  evidence,
  onClose,
}: {
  node: ClassificationTreeNode | null;
  evidence: Map<string, ClassificationEvidence>;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (node && dialog && !dialog.open) dialog.showModal();
    if (!node && dialog?.open) dialog.close();
  }, [node]);

  const items = node
    ? node.evidenceIds
      .map((id) => evidence.get(id))
      .filter((item): item is ClassificationEvidence => Boolean(item))
    : [];

  return (
    <dialog
      ref={dialogRef}
      className="classification-drawer"
      aria-labelledby="classification-drawer-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {node && (
        <div className="classification-drawer-panel">
          <header className="classification-drawer-header">
            <div>
              <p className="caption">{nodeLabel[node.nodeType]}</p>
              <h3 id="classification-drawer-title" className="heading mt-1">
                {node.htsCode && <span className="mono mr-2">{node.htsCode}</span>}
                {node.title}
              </h3>
            </div>
            <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="关闭详情">
              关闭
            </button>
          </header>
          <div className="classification-drawer-body">
            <span className={`classification-node-status classification-node-status--${node.status}`}>
              {statusLabel[node.status]}
            </span>
            {node.rationale.length > 0 && (
              <section className="mt-5">
                <h4 className="subheading mb-2">判断理由</h4>
                <ul className="list-disc pl-5 body space-y-1">
                  {node.rationale.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
                </ul>
              </section>
            )}
            {node.missingInformation.length > 0 && (
              <section className="mt-5">
                <h4 className="subheading mb-2 text-amber-800">待确认条件</h4>
                <ul className="list-disc pl-5 body space-y-1 text-amber-900">
                  {node.missingInformation.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </section>
            )}
            <section className="mt-5">
              <h4 className="subheading mb-2">逐条证据（{items.length}）</h4>
              {items.length > 0 ? (
                <ul className="space-y-3">
                  {items.map((item) => <EvidenceItem key={item.id} item={item} />)}
                </ul>
              ) : (
                <p className="caption">该节点没有单独引用证据。</p>
              )}
            </section>
          </div>
        </div>
      )}
    </dialog>
  );
}

export function ClassificationTreeView({ tree }: { tree: ClassificationTree }) {
  const [selectedNode, setSelectedNode] = useState<ClassificationTreeNode | null>(null);
  const layout = useMemo(() => buildDecisionTreeLayout(tree), [tree]);
  const evidence = useMemo(
    () => new Map(tree.evidence.map((item) => [item.id, item])),
    [tree.evidence],
  );

  return (
    <section className="card p-5 sm:p-6 overflow-hidden">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="heading">分类思路树</h2>
          <p className="caption mt-1">从左向右查看分类路径；点击节点查看完整理由和证据。</p>
        </div>
        <div className="flex gap-2 text-xs" aria-label="节点状态图例">
          <span className="classification-node-status classification-node-status--selected">选中</span>
          <span className="classification-node-status classification-node-status--excluded">排除</span>
          <span className="classification-node-status classification-node-status--pending">待确认</span>
        </div>
      </div>

      <div className="decision-tree-scroll mt-5">
        <div className="decision-tree-canvas">
          <NodeButton node={layout.root} onOpen={setSelectedNode} />
          <span className="decision-arrow" aria-hidden="true" />
          <div className="decision-rule-stage">
            <span className="decision-stage-label">适用规则</span>
            {layout.rules.length > 0 ? layout.rules.map((rule) => (
              <NodeButton key={rule.id} node={rule} onOpen={setSelectedNode} />
            )) : <div className="decision-empty-node">未返回明确规则</div>}
          </div>
          <span className="decision-arrow" aria-hidden="true" />
          <div className="decision-candidate-branches">
            {layout.headings.map((heading) => (
              <div className="decision-candidate-path" key={heading.id}>
                <Path node={heading} onOpen={setSelectedNode} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <EvidenceDrawer node={selectedNode} evidence={evidence} onClose={() => setSelectedNode(null)} />
    </section>
  );
}

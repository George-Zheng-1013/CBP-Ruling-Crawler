import { useState } from 'react';
import { buildRulingPdfUrl } from '../../api/rulings';
import { RulingDetailFE } from '../../types/ruling';
import { StatusBadge } from '../common/StatusBadge';
import { DescriptionPanel } from './DescriptionPanel';
import { HSCodeList } from './HSCodeList';
import { ParseFailedBadge } from './ParseFailedBadge';
import { formatDate, formatYear } from '../../utils/format';

interface Props {
  ruling: RulingDetailFE;
}

export function DetailView({ ruling }: Props) {
  const [copied, setCopied] = useState(false);

  const copyNo = async () => {
    try {
      await navigator.clipboard.writeText(ruling.rulingNo);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 剪贴板不可用时静默忽略 */
    }
  };

  return (
    <div className="card p-4 sm:p-6">
      {/* Header */}
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div>
          <p className="mono text-navy font-bold text-lg">{ruling.rulingNo}</p>
          <h1 className="heading mt-1">{ruling.subject || '(无主题)'}</h1>
        </div>
        <StatusBadge status={ruling.status} size="medium" />
      </div>

      {/* Meta */}
      <div className="flex gap-5 mt-3 caption flex-wrap">
        <span>年份：{formatYear(ruling.year)}</span>
        <span>裁定日期：{formatDate(ruling.rulingDate)}</span>
        <span>状态：{ruling.status}</span>
      </div>

      <HSCodeList mainHsCode={ruling.hsCode} hsCodes={ruling.hsCodes} />

      {ruling.parseFailed && <ParseFailedBadge message={ruling.parseErrorMsg} />}

      <DescriptionPanel text={ruling.description} />

      {/* Actions */}
      <div className="flex gap-3 mt-4 flex-wrap">
        {ruling.detailUrl && (
          <a
            className="btn btn-primary text-sm"
            href={ruling.detailUrl}
            target="_blank"
            rel="noreferrer"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            打开官方链接
          </a>
        )}
        <button className="btn btn-outline text-sm" onClick={copyNo}>
          {copied ? '已复制' : '复制编号'}
        </button>
        <a
          className="btn btn-outline text-sm"
          href={buildRulingPdfUrl(ruling.rulingNo)}
          download={`${ruling.rulingNo}.pdf`}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 3v12" />
            <polyline points="7 10 12 15 17 10" />
            <path d="M5 21h14" />
          </svg>
          下载 PDF
        </a>
      </div>
    </div>
  );
}

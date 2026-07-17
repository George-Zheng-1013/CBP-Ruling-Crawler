import { useState } from 'react';
import { useQueryStore } from '../../store/queryStore';

export function SearchBar() {
  const keyword = useQueryStore((s) => s.keyword);
  const rulingNo = useQueryStore((s) => s.rulingNo);
  const setKeyword = useQueryStore((s) => s.setKeyword);
  const setRulingNo = useQueryStore((s) => s.setRulingNo);

  const [kw, setKw] = useState(keyword);
  const [no, setNo] = useState(rulingNo);

  const submit = () => {
    setKeyword(kw.trim());
    setRulingNo(no.trim());
  };

  return (
    <div className="card p-3 flex flex-wrap gap-3 items-center">
      <input
        className="input flex-1 min-w-[200px]"
        placeholder="关键词 — 匹配主题或全文描述"
        value={kw}
        onChange={(e) => setKw(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
      />
      <input
        className="input w-[180px]"
        placeholder="裁定编号 — 如 N12345"
        value={no}
        onChange={(e) => setNo(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
      />
      <button className="btn btn-primary" onClick={submit}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        搜索
      </button>
    </div>
  );
}

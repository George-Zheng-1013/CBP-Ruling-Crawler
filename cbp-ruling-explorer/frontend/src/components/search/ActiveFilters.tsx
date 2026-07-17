import { useQueryStore } from '../../store/queryStore';

export function ActiveFilters() {
  const { keyword, rulingNo, year, status, hsCode } = useQueryStore();
  const setKeyword = useQueryStore((s) => s.setKeyword);
  const setRulingNo = useQueryStore((s) => s.setRulingNo);
  const setYear = useQueryStore((s) => s.setYear);
  const setStatus = useQueryStore((s) => s.setStatus);
  const setHsCode = useQueryStore((s) => s.setHsCode);

  const chips: { key: string; label: string; onDelete: () => void }[] = [];
  if (keyword)
    chips.push({ key: 'kw', label: `关键词: ${keyword}`, onDelete: () => setKeyword('') });
  if (rulingNo)
    chips.push({ key: 'no', label: `编号: ${rulingNo}`, onDelete: () => setRulingNo('') });
  if (year != null)
    chips.push({ key: 'yr', label: `年份: ${year}`, onDelete: () => setYear(null) });
  if (status)
    chips.push({ key: 'st', label: `状态: ${status}`, onDelete: () => setStatus('') });
  if (hsCode)
    chips.push({ key: 'hs', label: `HS: ${hsCode}`, onDelete: () => setHsCode('') });

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {chips.map((c) => (
        <span key={c.key} className="chip chip-accent">
          {c.label}
          <button
            className="ml-1 hover:text-navy cursor-pointer"
            onClick={c.onDelete}
            aria-label="移除"
          >
            ×
          </button>
        </span>
      ))}
    </div>
  );
}

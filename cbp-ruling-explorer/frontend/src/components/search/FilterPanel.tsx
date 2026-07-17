import { useQueryStore } from '../../store/queryStore';

interface Props {
  yearOptions: number[];
  statusOptions: string[];
}

export function FilterPanel({ yearOptions, statusOptions }: Props) {
  const year = useQueryStore((s) => s.year);
  const status = useQueryStore((s) => s.status);
  const hsCode = useQueryStore((s) => s.hsCode);
  const setYear = useQueryStore((s) => s.setYear);
  const setStatus = useQueryStore((s) => s.setStatus);
  const setHsCode = useQueryStore((s) => s.setHsCode);
  const reset = useQueryStore((s) => s.reset);

  return (
    <div className="card p-3 flex flex-col gap-3">
      <div>
        <label className="caption block mb-1">年份</label>
        <select
          className="select w-full"
          value={year ?? ''}
          onChange={(e) =>
            setYear(e.target.value ? Number(e.target.value) : null)
          }
        >
          <option value="">全部</option>
          {yearOptions.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="caption block mb-1">状态</label>
        <select
          className="select w-full"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">全部</option>
          {statusOptions.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="caption block mb-1">HS Code 前缀</label>
        <input
          className="input w-full"
          placeholder="如 8517"
          value={hsCode}
          onChange={(e) => setHsCode(e.target.value.trim())}
        />
      </div>

      <button className="btn btn-ghost text-sm !text-muted" onClick={reset}>
        清除筛选
      </button>
    </div>
  );
}

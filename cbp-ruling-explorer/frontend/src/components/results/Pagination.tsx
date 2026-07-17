import { useQueryStore } from '../../store/queryStore';
import { PageResult } from '../../types/ruling';

interface Props {
  result: PageResult<unknown>;
}

export function Pagination({ result }: Props) {
  const setPage = useQueryStore((s) => s.setPage);
  if (result.totalPages <= 1) return null;

  const pages: number[] = [];
  const start = Math.max(1, result.page - 2);
  const end = Math.min(result.totalPages, result.page + 2);
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="flex justify-center items-center gap-1 mt-6">
      <button
        className="btn btn-ghost text-sm !px-2"
        disabled={result.page <= 1}
        onClick={() => setPage(1)}
      >
        «
      </button>
      <button
        className="btn btn-ghost text-sm !px-2"
        disabled={result.page <= 1}
        onClick={() => setPage(result.page - 1)}
      >
        ‹
      </button>
      {start > 1 && <span className="px-1 caption">…</span>}
      {pages.map((p) => (
        <button
          key={p}
          className={`btn text-sm !px-2.5 min-w-[32px] ${
            p === result.page ? 'btn-primary' : 'btn-ghost'
          }`}
          onClick={() => setPage(p)}
        >
          {p}
        </button>
      ))}
      {end < result.totalPages && <span className="px-1 caption">…</span>}
      <button
        className="btn btn-ghost text-sm !px-2"
        disabled={result.page >= result.totalPages}
        onClick={() => setPage(result.page + 1)}
      >
        ›
      </button>
      <button
        className="btn btn-ghost text-sm !px-2"
        disabled={result.page >= result.totalPages}
        onClick={() => setPage(result.totalPages)}
      >
        »
      </button>
    </div>
  );
}

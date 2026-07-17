import { useState } from 'react';
import { buildExportUrl } from '../../api/rulings';
import { useQueryStore } from '../../store/queryStore';
import { ExportFormat } from '../../types/ruling';

export function ExportButton() {
  const [open, setOpen] = useState(false);
  const { keyword, rulingNo, year, status, hsCode } = useQueryStore();

  const handleExport = (format: ExportFormat) => {
    setOpen(false);
    const url = buildExportUrl(
      {
        keyword,
        rulingNo,
        year: year ?? undefined,
        status,
        hsCode,
        pageSize: 25,
        sort: 'year_desc',
      },
      format,
    );
    window.open(url, '_blank');
  };

  return (
    <div className="relative">
      <button
        className="btn btn-outline text-sm"
        onClick={() => setOpen(!open)}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        导出
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 card p-1.5 z-40 shadow-lg min-w-[120px]">
            <button
              className="btn btn-ghost text-sm w-full !justify-start"
              onClick={() => handleExport('csv')}
            >
              导出 CSV
            </button>
            <button
              className="btn btn-ghost text-sm w-full !justify-start"
              onClick={() => handleExport('json')}
            >
              导出 JSON
            </button>
          </div>
        </>
      )}
    </div>
  );
}

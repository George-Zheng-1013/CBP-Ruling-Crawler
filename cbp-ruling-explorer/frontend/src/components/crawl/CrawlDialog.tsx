import { useState } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (minDate: string) => void;
}

export function CrawlDialog({ open, onClose, onConfirm }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [minDate, setMinDate] = useState('2025-01-01');

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Dialog */}
      <div className="relative card p-6 w-full max-w-sm mx-4 shadow-xl">
        <h2 className="heading mb-2">全库数据同步</h2>
        <p className="caption mb-4">
          指定起始日期，从该日期起检查并同步所有 HQ/NY/N 系列裁定
          （更新已有记录 + 新增裁定，不会清空已有数据）。
        </p>
        <input
          type="date"
          className="input w-full"
          value={minDate}
          min="2000-01-01"
          max={today}
          onChange={(e) => setMinDate(e.target.value)}
        />
        <div className="flex justify-end gap-2 mt-5">
          <button className="btn btn-ghost text-sm" onClick={onClose}>
            取消
          </button>
          <button
            className="btn btn-primary text-sm"
            disabled={!minDate}
            onClick={() => minDate && onConfirm(minDate)}
          >
            开始同步
          </button>
        </div>
      </div>
    </div>
  );
}

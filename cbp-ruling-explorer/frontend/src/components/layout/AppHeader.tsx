import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { startIncremental, startSync } from '../../api/crawl';
import { CrawlDialog } from '../crawl/CrawlDialog';
import { CrawlProgressBar } from '../crawl/CrawlProgressBar';

function NavButton({
  to,
  label,
  active,
}: {
  to: string;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      to={to}
      className={`btn btn-ghost text-sm !text-white/80 hover:!text-white hover:!bg-white/10 ${
        active ? '!bg-white/15 !text-white' : ''
      }`}
    >
      {label}
    </Link>
  );
}

export function AppHeader() {
  const location = useLocation();
  const isSearch = location.pathname === '/';
  const isClassify = location.pathname === '/classify';
  const isStats = location.pathname === '/stats';

  const [crawlRunning, setCrawlRunning] = useState(false);
  const [crawlType, setCrawlType] = useState<'incremental' | 'sync' | null>(null);
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null);
  const [syncDialogOpen, setSyncDialogOpen] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const onCrawlStateChange = useCallback(
    (newStatus: string, message?: string) => {
      if (newStatus === 'completed') {
        setCrawlRunning(false);
        setCrawlMessage(null);
        setCrawlType(null);
        setToast({
          msg: `${crawlType === 'incremental' ? '增量更新' : '全库同步'}完成`,
          ok: true,
        });
      } else if (newStatus === 'failed') {
        setCrawlRunning(false);
        setCrawlMessage(null);
        setCrawlType(null);
        setToast({ msg: `爬取失败: ${message || '未知错误'}`, ok: false });
      }
    },
    [crawlType],
  );

  const handleIncremental = async () => {
    if (crawlRunning) return;
    setCrawlType('incremental');
    setCrawlMessage('正在启动增量更新…');
    setCrawlRunning(true);
    try {
      await startIncremental();
      setCrawlMessage('增量更新运行中…');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '启动失败';
      setCrawlRunning(false);
      setCrawlType(null);
      setCrawlMessage(null);
      setToast({ msg, ok: false });
    }
  };

  const handleSync = async (minDate: string) => {
    setSyncDialogOpen(false);
    if (crawlRunning) return;
    setCrawlType('sync');
    setCrawlMessage('正在启动全库同步…');
    setCrawlRunning(true);
    try {
      await startSync(minDate);
      setCrawlMessage('全库同步运行中…');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '启动失败';
      setCrawlRunning(false);
      setCrawlType(null);
      setCrawlMessage(null);
      setToast({ msg, ok: false });
    }
  };

  return (
    <>
      <header className="bg-navy sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-12 flex items-center gap-1">
          {/* Brand */}
          <Link to="/" className="text-white font-bold text-[15px] tracking-tight mr-3 shrink-0">
            CBP Ruling Explorer
          </Link>

          <div className="flex-1" />

          {/* Nav */}
          <NavButton to="/" label="查询" active={isSearch} />
          <NavButton to="/classify" label="智能归类" active={isClassify} />
          <NavButton to="/stats" label="统计概览" active={isStats} />

          {/* Separator */}
          <div className="w-px h-4 bg-white/20 mx-2" />

          {/* Crawl actions */}
          <button
            className="btn btn-ghost text-sm !text-white/80 hover:!text-white hover:!bg-white/10"
            disabled={crawlRunning}
            onClick={handleIncremental}
          >
            {crawlRunning && crawlType === 'incremental' ? '增量更新中…' : '增量更新'}
          </button>
          <button
            className="btn btn-ghost text-sm !text-white/80 hover:!text-white hover:!bg-white/10"
            disabled={crawlRunning}
            onClick={() => setSyncDialogOpen(true)}
          >
            {crawlRunning && crawlType === 'sync' ? '同步中…' : '全库同步'}
          </button>
        </div>

        {/* Progress bar */}
        <CrawlProgressBar active={crawlRunning} onStateChange={onCrawlStateChange} />
      </header>

      <CrawlDialog
        open={syncDialogOpen}
        onClose={() => setSyncDialogOpen(false)}
        onConfirm={handleSync}
      />

      {/* Toast */}
      {toast && <Toast message={toast.msg} ok={toast.ok} onDone={() => setToast(null)} />}
    </>
  );
}

/* ── Toast (auto-dismiss) ── */
function Toast({
  message,
  ok,
  onDone,
}: {
  message: string;
  ok: boolean;
  onDone: () => void;
}) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  // ponytail: 仅 mount 时设一次定时器，避免每次渲染重置
  if (!timerRef.current) {
    timerRef.current = setTimeout(onDone, 5000);
  }
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
      <div
        className={`px-5 py-2.5 rounded-md shadow-lg text-sm font-medium ${
          ok ? 'bg-green-700 text-white' : 'bg-red-700 text-white'
        }`}
      >
        {message}
      </div>
    </div>
  );
}

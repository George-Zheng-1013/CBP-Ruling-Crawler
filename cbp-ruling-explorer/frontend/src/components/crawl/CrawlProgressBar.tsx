import { useEffect, useState, useRef } from 'react';
import { getCrawlStatus } from '../../api/crawl';

interface Props {
  active: boolean;
  onStateChange?: (newStatus: string, message?: string) => void;
}

export function CrawlProgressBar({ active, onStateChange }: Props) {
  const [statusText, setStatusText] = useState('正在爬取…');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!active) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(async () => {
      try {
        const status = await getCrawlStatus();
        if (status.status === 'completed') {
          setStatusText('爬取完成');
          onStateChange?.('completed');
          setTimeout(() => {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }, 3000);
        } else if (status.status === 'failed') {
          setStatusText(
            `爬取失败: ${status.errorMessage?.slice(0, 80) || '未知错误'}`
          );
          onStateChange?.('failed', status.errorMessage ?? undefined);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        } else if (status.status === 'running') {
          const tail = status.logTail || '';
          const lines = tail.split('\n').filter((l) => l.trim());
          const last = lines[lines.length - 1] || '';
          setStatusText(last.length > 80 ? last.slice(0, 80) + '…' : last || '正在爬取…');
        }
      } catch {
        /* silent */
      }
    }, 5000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active, onStateChange]);

  if (!active) return null;

  return (
    <div className="px-4 py-1.5 bg-surface border-b border-border">
      <div className="progress-bar mb-1" />
      <span className="caption font-mono text-[11px]">{statusText}</span>
    </div>
  );
}

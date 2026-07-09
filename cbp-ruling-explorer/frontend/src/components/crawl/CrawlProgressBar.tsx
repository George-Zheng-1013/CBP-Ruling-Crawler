import { useEffect, useState, useRef } from 'react';
import { Box, LinearProgress, Typography } from '@mui/material';
import { getCrawlStatus } from '../../api/crawl';

interface CrawlProgressBarProps {
  /** 当前是否正在运行（由父组件控制显示） */
  active: boolean;
  /** 状态变更回调：运行完成或失败时通知父组件 */
  onStateChange?: (newStatus: string, message?: string) => void;
}

export function CrawlProgressBar({ active, onStateChange }: CrawlProgressBarProps) {
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

    // 每 5 秒轮询一次状态
    intervalRef.current = setInterval(async () => {
      try {
        const status = await getCrawlStatus();
        if (status.status === 'completed') {
          setStatusText('爬取完成');
          onStateChange?.('completed');
          // 延迟清理
          setTimeout(() => {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }, 3000);
        } else if (status.status === 'failed') {
          setStatusText(`爬取失败: ${status.errorMessage?.slice(0, 80) || '未知错误'}`);
          onStateChange?.('failed', status.errorMessage ?? undefined);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        } else if (status.status === 'running') {
          // 从 log_tail 中提取最后一条有意义的行作为状态文本
          const tail = status.logTail || '';
          const lines = tail.split('\n').filter((l) => l.trim());
          const lastLine = lines[lines.length - 1] || '';
          setStatusText(lastLine.length > 80 ? lastLine.slice(0, 80) + '…' : lastLine || '正在爬取…');
        }
      } catch {
        // 轮询失败静默处理
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
    <Box
      sx={{
        px: 2,
        py: 0.5,
        backgroundColor: 'background.paper',
        borderBottom: '0.5px solid',
        borderColor: 'divider',
      }}
    >
      <LinearProgress sx={{ mb: 0.5 }} />
      <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: 11 }}>
        {statusText}
      </Typography>
    </Box>
  );
}

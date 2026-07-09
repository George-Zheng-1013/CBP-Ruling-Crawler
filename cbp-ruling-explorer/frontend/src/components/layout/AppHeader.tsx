import { useCallback, useState } from 'react';
import { AppBar, Box, Button, Divider, Snackbar, Toolbar, Typography } from '@mui/material';
import { Link, useLocation } from 'react-router-dom';
import SearchIcon from '@mui/icons-material/Search';
import BarChartIcon from '@mui/icons-material/BarChart';
import SyncIcon from '@mui/icons-material/Sync';
import CloudSyncIcon from '@mui/icons-material/CloudSync';

import { startIncremental, startSync } from '../../api/crawl';
import { CrawlDialog } from '../crawl/CrawlDialog';
import { CrawlProgressBar } from '../crawl/CrawlProgressBar';

export function AppHeader() {
  const location = useLocation();
  const isSearch = location.pathname === '/';
  const isStats = location.pathname === '/stats';

  // 爬虫任务状态
  const [crawlRunning, setCrawlRunning] = useState(false);
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null);
  const [crawlType, setCrawlType] = useState<'incremental' | 'sync' | null>(null);
  const [syncDialogOpen, setSyncDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: 'success' | 'error' } | null>(null);

  const onCrawlStateChange = useCallback((newStatus: string, message?: string) => {
    if (newStatus === 'completed') {
      setCrawlRunning(false);
      setCrawlMessage(null);
      setCrawlType(null);
      setSnackbar({ msg: `${crawlType === 'incremental' ? '增量更新' : '全库同步'}完成`, severity: 'success' });
    } else if (newStatus === 'failed') {
      setCrawlRunning(false);
      setCrawlMessage(null);
      setCrawlType(null);
      setSnackbar({ msg: `爬取失败: ${message || '未知错误'}`, severity: 'error' });
    }
  }, [crawlType]);

  const handleIncremental = async () => {
    if (crawlRunning) return;
    setCrawlType('incremental');
    setCrawlMessage('正在启动增量更新…');
    setCrawlRunning(true);
    try {
      const result = await startIncremental();
      setCrawlMessage(`增量更新已启动，从 ${result.minDate} 起爬取`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '启动失败';
      setCrawlRunning(false);
      setCrawlType(null);
      setCrawlMessage(null);
      setSnackbar({ msg, severity: 'error' });
    }
  };

  const handleSync = async (minDate: string) => {
    setSyncDialogOpen(false);
    if (crawlRunning) return;
    setCrawlType('sync');
    setCrawlMessage('正在启动全库同步…');
    setCrawlRunning(true);
    try {
      const result = await startSync(minDate);
      setCrawlMessage(`全库同步已启动，从 ${result.minDate} 起爬取`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '启动失败';
      setCrawlRunning(false);
      setCrawlType(null);
      setCrawlMessage(null);
      setSnackbar({ msg, severity: 'error' });
    }
  };

  return (
    <>
      <AppBar position="sticky" elevation={1}>
        <Toolbar>
          <Typography variant="h6" sx={{ fontWeight: 700, flexShrink: 0 }}>
            CBP Ruling Explorer
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          {/* 导航按钮 */}
          <Button
            component={Link}
            to="/"
            color="inherit"
            startIcon={<SearchIcon />}
            variant={isSearch ? 'contained' : 'text'}
            sx={{
              mr: 1,
              backgroundColor: isSearch ? 'rgba(255,255,255,0.15)' : 'transparent',
            }}
          >
            查询
          </Button>
          <Button
            component={Link}
            to="/stats"
            color="inherit"
            startIcon={<BarChartIcon />}
            variant={isStats ? 'contained' : 'text'}
            sx={{
              mr: 1,
              backgroundColor: isStats ? 'rgba(255,255,255,0.15)' : 'transparent',
            }}
          >
            统计概览
          </Button>
          <Divider orientation="vertical" flexItem sx={{ mx: 1, borderColor: 'rgba(255,255,255,0.3)' }} />
          {/* 爬虫操作按钮 */}
          <Button
            color="inherit"
            startIcon={<SyncIcon />}
            disabled={crawlRunning}
            onClick={handleIncremental}
            sx={{ mr: 1 }}
          >
            {crawlRunning && crawlType === 'incremental' ? '增量更新中…' : '增量更新'}
          </Button>
          <Button
            color="inherit"
            startIcon={<CloudSyncIcon />}
            disabled={crawlRunning}
            onClick={() => setSyncDialogOpen(true)}
          >
            {crawlRunning && crawlType === 'sync' ? '同步中…' : '全库同步'}
          </Button>
        </Toolbar>
      </AppBar>
      {/* 爬虫运行时的进度条 */}
      <CrawlProgressBar active={crawlRunning} onStateChange={onCrawlStateChange} />
      {/* 全库同步对话框 */}
      <CrawlDialog
        open={syncDialogOpen}
        onClose={() => setSyncDialogOpen(false)}
        onConfirm={handleSync}
      />
      {/* 结果通知 */}
      {snackbar && (
        <Snackbar
          open
          autoHideDuration={6000}
          onClose={() => setSnackbar(null)}
          message={snackbar.msg}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        />
      )}
    </>
  );
}

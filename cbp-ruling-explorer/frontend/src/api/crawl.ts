import client from './client';

export interface CrawlStartResult {
  status: string;       // started | conflict
  minDate: string;
  message: string;
}

export interface CrawlJobStatus {
  status: string;       // idle | running | completed | failed
  minDate: string;
  pid: number | null;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
  logTail: string;
}

/** 增量更新：从库中最新裁定日期起爬取。 */
export async function startIncremental(): Promise<CrawlStartResult> {
  const res = await client.post('/api/crawl/incremental');
  return res.data as CrawlStartResult;
}

/** 全库同步：从指定日期起检查并同步所有裁定。 */
export async function startSync(minDate: string): Promise<CrawlStartResult> {
  const res = await client.post('/api/crawl/sync', { min_date: minDate });
  return res.data as CrawlStartResult;
}

/** 查询当前爬虫任务状态。 */
export async function getCrawlStatus(): Promise<CrawlJobStatus> {
  const res = await client.get('/api/crawl/status');
  return res.data as CrawlJobStatus;
}

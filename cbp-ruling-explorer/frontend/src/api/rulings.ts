import client, { API_BASE } from './client';
import {
  ExportFormat,
  HtmlContentFE,
  PageResult,
  QueryState,
  RulingDetailFE,
  RulingItemFE,
  StatsOverviewFE,
} from '../types/ruling';

export interface RulingsQuery
  extends Partial<Omit<QueryState, 'page'>> {
  page?: number;
  pageSize?: number;
  sort?: string;
}

/** 将查询状态转换为后端需要的 snake_case 查询参数。 */
function buildParams(
  query: RulingsQuery,
): Record<string, string | number | undefined> {
  const params: Record<string, string | number | undefined> = {};
  if (query.keyword) params.keyword = query.keyword;
  if (query.rulingNo) params.ruling_no = query.rulingNo;
  if (query.year != null) params.year = query.year;
  if (query.status) params.status = query.status;
  if (query.hsCode) params.hs_code = query.hsCode;
  if (query.page != null) params.page = query.page;
  if (query.pageSize != null) params.page_size = query.pageSize;
  if (query.sort) params.sort = query.sort;
  return params;
}

/** 获取过滤 + 分页的裁定列表。 */
export async function getRulings(
  query: RulingsQuery,
): Promise<PageResult<RulingItemFE>> {
  const res = await client.get<PageResult<RulingItemFE>>('/api/rulings', {
    params: buildParams(query),
  });
  return res.data;
}

/** 获取单条裁定详情。 */
export async function getRulingDetail(
  rulingNo: string,
): Promise<RulingDetailFE> {
  const res = await client.get<RulingDetailFE>(
    `/api/rulings/${encodeURIComponent(rulingNo)}`,
  );
  return res.data;
}

/** 获取统计概览。 */
export async function getStats(): Promise<StatsOverviewFE> {
  const res = await client.get<StatsOverviewFE>('/api/stats/overview');
  return res.data;
}

/** 获取裁定原文 HTML（P2）。 */
export async function getRulingHtml(
  rulingNo: string,
): Promise<HtmlContentFE> {
  const res = await client.get<HtmlContentFE>(
    `/api/rulings/${encodeURIComponent(rulingNo)}/html`,
  );
  return res.data;
}

/** 拼接导出下载地址（当前筛选条件全集）。 */
export function buildExportUrl(
  query: RulingsQuery,
  format: ExportFormat,
): string {
  const params = buildParams(query);
  params.format = format;
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '') search.append(k, String(v));
  });
  return `${API_BASE}/api/rulings/export?${search.toString()}`;
}

// 前端 TypeScript 类型（camelCase）。
// 后端返回的 snake_case 字段经 api/client.ts 拦截器自动转换。

export interface RulingItemFE {
  rulingNo: string;
  subject: string;
  year: number;
  hsCode: string;
  hsCodes: string[];
  status: string;
  parseFailed: boolean;
}

export interface RulingDetailFE extends RulingItemFE {
  description: string;
  rulingDate: string;
  detailUrl: string;
  parseErrorMsg: string;
}

export interface YearCountFE {
  year: number;
  count: number;
}

export interface StatusCountFE {
  status: string;
  count: number;
}

export interface StatsOverviewFE {
  total: number;
  parseFailed: number;
  byYear: YearCountFE[];
  byStatus: StatusCountFE[];
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface QueryState {
  keyword: string;
  rulingNo: string;
  year: number | null;
  status: string;
  hsCode: string;
  page: number;
}

export type ExportFormat = 'csv' | 'json';

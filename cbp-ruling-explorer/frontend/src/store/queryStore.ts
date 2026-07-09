import { create } from 'zustand';
import { QueryState } from '../types/ruling';

interface QueryStore extends QueryState {
  reloadToken: number;
  setKeyword: (v: string) => void;
  setRulingNo: (v: string) => void;
  setYear: (v: number | null) => void;
  setStatus: (v: string) => void;
  setHsCode: (v: string) => void;
  setPage: (v: number) => void;
  reset: () => void;
  reload: () => void;
  toParams: () => Record<string, string | number | undefined>;
}

const DEFAULT: QueryState = {
  keyword: '',
  rulingNo: '',
  year: null,
  status: '',
  hsCode: '',
  page: 1,
};

/** 从当前 URL 解析查询状态（支持刷新/分享后保留筛选条件）。 */
function parseUrl(): QueryState {
  const params = new URLSearchParams(window.location.search);
  const yearRaw = params.get('year');
  return {
    keyword: params.get('keyword') ?? '',
    rulingNo: params.get('ruling_no') ?? '',
    year: yearRaw ? Number(yearRaw) : null,
    status: params.get('status') ?? '',
    hsCode: params.get('hs_code') ?? '',
    page: params.get('page') ? Number(params.get('page')) : 1,
  };
}

/** 将查询状态写回 URL（replaceState，不新增历史记录）。 */
function syncUrl(state: QueryState): void {
  const params = new URLSearchParams();
  if (state.keyword) params.set('keyword', state.keyword);
  if (state.rulingNo) params.set('ruling_no', state.rulingNo);
  if (state.year != null) params.set('year', String(state.year));
  if (state.status) params.set('status', state.status);
  if (state.hsCode) params.set('hs_code', state.hsCode);
  if (state.page && state.page > 1) params.set('page', String(state.page));
  const query = params.toString();
  const url = `${window.location.pathname}${query ? `?${query}` : ''}`;
  window.history.replaceState(null, '', url);
}

const initial: QueryState =
  typeof window !== 'undefined' ? parseUrl() : DEFAULT;

export const useQueryStore = create<QueryStore>((set, get) => {
  const apply = (partial: Partial<QueryState>, resetPage = true) => {
    set((prev) => {
      const next = { ...prev, ...partial };
      if (resetPage) next.page = 1;
      syncUrl(next);
      return next;
    });
  };
  return {
    ...initial,
    reloadToken: 0,
    setKeyword: (v) => apply({ keyword: v }),
    setRulingNo: (v) => apply({ rulingNo: v }),
    setYear: (v) => apply({ year: v }),
    setStatus: (v) => apply({ status: v }),
    setHsCode: (v) => apply({ hsCode: v }),
    setPage: (v) => apply({ page: v }, false),
    reset: () => {
      set({ ...DEFAULT });
      syncUrl({ ...DEFAULT });
    },
    reload: () => set((s) => ({ reloadToken: s.reloadToken + 1 })),
    toParams: () => {
      const s = get();
      return {
        keyword: s.keyword,
        ruling_no: s.rulingNo,
        year: s.year ?? undefined,
        status: s.status,
        hs_code: s.hsCode,
        page: s.page,
      };
    },
  };
});

import { useEffect, useState } from 'react';
import { getRulings } from '../api/rulings';
import { PageResult, RulingItemFE } from '../types/ruling';
import { useQueryStore } from '../store/queryStore';

interface UseRulingsResult {
  data: PageResult<RulingItemFE> | null;
  loading: boolean;
  error: string | null;
}

/** 列表查询 hook：监听查询状态变化（含 reloadToken）并拉取数据。 */
export function useRulings(): UseRulingsResult {
  const keyword = useQueryStore((s) => s.keyword);
  const rulingNo = useQueryStore((s) => s.rulingNo);
  const year = useQueryStore((s) => s.year);
  const status = useQueryStore((s) => s.status);
  const hsCode = useQueryStore((s) => s.hsCode);
  const page = useQueryStore((s) => s.page);
  const reloadToken = useQueryStore((s) => s.reloadToken);

  const [data, setData] = useState<PageResult<RulingItemFE> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    // 防抖 300ms，避免输入/筛选高频触发请求。
    const timer = setTimeout(() => {
      setLoading(true);
      getRulings({
        keyword,
        rulingNo,
        year: year ?? undefined,
        status,
        hsCode,
        page,
        pageSize: 25,
        sort: 'year_desc',
      })
        .then((res) => {
          if (!controller.signal.aborted) {
            setData(res);
            setError(null);
          }
        })
        .catch((err: Error) => {
          if (!controller.signal.aborted) {
            setError(err.message);
            setData(null);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 300);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [keyword, rulingNo, year, status, hsCode, page, reloadToken]);

  return { data, loading, error };
}

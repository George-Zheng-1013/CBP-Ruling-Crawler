import { useEffect, useState } from 'react';
import { getStats } from '../api/rulings';
import { StatsOverviewFE } from '../types/ruling';

interface UseStatsResult {
  data: StatsOverviewFE | null;
  loading: boolean;
  error: string | null;
}

/** 统计查询 hook：挂载时拉取一次统计概览。 */
export function useStats(): UseStatsResult {
  const [data, setData] = useState<StatsOverviewFE | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getStats()
      .then((res) => {
        if (active) {
          setData(res);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
          setData(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { data, loading, error };
}

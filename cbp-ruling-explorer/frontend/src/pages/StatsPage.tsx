import { useStats } from '../hooks/useStats';
import { StatsOverview } from '../components/stats/StatsOverview';
import { Loading } from '../components/common/Loading';
import { ErrorState } from '../components/common/ErrorBoundary';

export function StatsPage() {
  const { data, loading, error } = useStats();
  return (
    <div>
      <h1 className="heading mb-4">统计概览</h1>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} />
      ) : data ? (
        <StatsOverview stats={data} />
      ) : null}
    </div>
  );
}

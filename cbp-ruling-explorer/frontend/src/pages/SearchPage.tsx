import { useRulings } from '../hooks/useRulings';
import { useStats } from '../hooks/useStats';
import { useQueryStore } from '../store/queryStore';
import { SearchBar } from '../components/search/SearchBar';
import { FilterPanel } from '../components/search/FilterPanel';
import { ActiveFilters } from '../components/search/ActiveFilters';
import { ResultList } from '../components/results/ResultList';
import { Pagination } from '../components/results/Pagination';
import { ExportButton } from '../components/common/ExportButton';
import { Loading } from '../components/common/Loading';
import { ErrorState } from '../components/common/ErrorBoundary';

export function SearchPage() {
  const { data, loading, error } = useRulings();
  const { data: stats } = useStats();
  const reload = useQueryStore((s) => s.reload);

  const yearOptions = (stats?.byYear ?? []).map((y) => y.year);
  const statusOptions = (stats?.byStatus ?? []).map((s) => s.status);

  return (
    <div className="flex flex-col md:flex-row gap-4">
      {/* Sidebar */}
      <aside className="md:w-56 shrink-0">
        <FilterPanel yearOptions={yearOptions} statusOptions={statusOptions} />
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0">
        <SearchBar />

        <div className="flex justify-between items-center mb-3 mt-4 flex-wrap gap-2">
          <span className="caption">
            {data && !loading ? `共 ${data.total.toLocaleString()} 条结果` : '\u00A0'}
          </span>
          <ExportButton />
        </div>

        <ActiveFilters />

        {!data && loading ? (
          <Loading />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : (
          <>
            <ResultList
              items={data?.items ?? []}
              loading={loading}
              error={error}
              onRetry={reload}
            />
            {data && <Pagination result={data} />}
          </>
        )}
      </div>
    </div>
  );
}

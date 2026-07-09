import { Box, Grid, Typography } from '@mui/material';
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
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <SearchBar />
      </Grid>
      <Grid item xs={12} md={3}>
        <FilterPanel yearOptions={yearOptions} statusOptions={statusOptions} />
      </Grid>
      <Grid item xs={12} md={9}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 1,
            flexWrap: 'wrap',
            gap: 1,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            {data && !loading ? `共 ${data.total} 条结果` : ' '}
          </Typography>
          <ExportButton />
        </Box>
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
      </Grid>
    </Grid>
  );
}

import { Box, Typography } from '@mui/material';
import { useStats } from '../hooks/useStats';
import { StatsOverview } from '../components/stats/StatsOverview';
import { Loading } from '../components/common/Loading';
import { ErrorState } from '../components/common/ErrorBoundary';

export function StatsPage() {
  const { data, loading, error } = useStats();
  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
        统计概览
      </Typography>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} />
      ) : data ? (
        <StatsOverview stats={data} />
      ) : null}
    </Box>
  );
}

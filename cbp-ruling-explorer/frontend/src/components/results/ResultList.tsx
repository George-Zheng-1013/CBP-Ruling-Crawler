import { Box, Typography } from '@mui/material';
import { RulingItemFE } from '../../types/ruling';
import { RulingCard } from './RulingCard';
import { Loading } from '../common/Loading';
import { ErrorState } from '../common/ErrorBoundary';

interface Props {
  items: RulingItemFE[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function ResultList({ items, loading, error, onRetry }: Props) {
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (items.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
        <Typography variant="h6">未找到匹配的裁定</Typography>
        <Typography variant="body2">试试调整关键词或筛选条件</Typography>
      </Box>
    );
  }
  return (
    <Box
      sx={{
        columns: { xs: 1, sm: 2, lg: 3 },
        columnGap: 2,
      }}
    >
      {items.map((r) => (
        <RulingCard ruling={r} key={r.rulingNo} />
      ))}
    </Box>
  );
}

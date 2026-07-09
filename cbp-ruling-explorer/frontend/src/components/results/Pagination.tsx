import { Box, Pagination as MuiPagination } from '@mui/material';
import { useQueryStore } from '../../store/queryStore';
import { PageResult } from '../../types/ruling';

interface Props {
  result: PageResult<unknown>;
}

export function Pagination({ result }: Props) {
  const setPage = useQueryStore((s) => s.setPage);
  if (result.totalPages <= 1) return null;
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
      <MuiPagination
        count={result.totalPages}
        page={result.page}
        onChange={(_, p) => setPage(p)}
        color="primary"
        showFirstButton
        showLastButton
      />
    </Box>
  );
}

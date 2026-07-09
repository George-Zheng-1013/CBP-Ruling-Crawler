import { Box, Chip } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { useQueryStore } from '../../store/queryStore';

export function ActiveFilters() {
  const { keyword, rulingNo, year, status, hsCode } = useQueryStore();
  const setKeyword = useQueryStore((s) => s.setKeyword);
  const setRulingNo = useQueryStore((s) => s.setRulingNo);
  const setYear = useQueryStore((s) => s.setYear);
  const setStatus = useQueryStore((s) => s.setStatus);
  const setHsCode = useQueryStore((s) => s.setHsCode);

  const chips: { key: string; label: string; onDelete: () => void }[] = [];
  if (keyword)
    chips.push({ key: 'kw', label: `关键词: ${keyword}`, onDelete: () => setKeyword('') });
  if (rulingNo)
    chips.push({ key: 'no', label: `编号: ${rulingNo}`, onDelete: () => setRulingNo('') });
  if (year != null)
    chips.push({ key: 'yr', label: `年份: ${year}`, onDelete: () => setYear(null) });
  if (status)
    chips.push({ key: 'st', label: `状态: ${status}`, onDelete: () => setStatus('') });
  if (hsCode)
    chips.push({ key: 'hs', label: `HS: ${hsCode}`, onDelete: () => setHsCode('') });

  if (chips.length === 0) return null;

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
      {chips.map((c) => (
        <Chip
          key={c.key}
          label={c.label}
          onDelete={c.onDelete}
          deleteIcon={<CloseIcon />}
          size="small"
        />
      ))}
    </Box>
  );
}

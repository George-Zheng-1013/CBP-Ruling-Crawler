import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
} from '@mui/material';
import ClearAllIcon from '@mui/icons-material/ClearAll';
import { useQueryStore } from '../../store/queryStore';

interface Props {
  yearOptions: number[];
  statusOptions: string[];
}

export function FilterPanel({ yearOptions, statusOptions }: Props) {
  const year = useQueryStore((s) => s.year);
  const status = useQueryStore((s) => s.status);
  const hsCode = useQueryStore((s) => s.hsCode);
  const setYear = useQueryStore((s) => s.setYear);
  const setStatus = useQueryStore((s) => s.setStatus);
  const setHsCode = useQueryStore((s) => s.setHsCode);
  const reset = useQueryStore((s) => s.reset);

  return (
    <Paper sx={{ p: 2 }} elevation={1}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <FormControl size="small" fullWidth>
          <InputLabel id="year-label">年份</InputLabel>
          <Select
            labelId="year-label"
            label="年份"
            value={year ?? ''}
            onChange={(e) => setYear(e.target.value ? Number(e.target.value) : null)}
          >
            <MenuItem value="">全部</MenuItem>
            {yearOptions.map((y) => (
              <MenuItem key={y} value={y}>
                {y}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" fullWidth>
          <InputLabel id="status-label">状态</InputLabel>
          <Select
            labelId="status-label"
            label="状态"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <MenuItem value="">全部</MenuItem>
            {statusOptions.map((s) => (
              <MenuItem key={s} value={s}>
                {s}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          label="HS Code 前缀"
          placeholder="如 8517"
          size="small"
          value={hsCode}
          onChange={(e) => setHsCode(e.target.value.trim())}
        />

        <Button
          variant="text"
          startIcon={<ClearAllIcon />}
          onClick={reset}
          color="inherit"
        >
          清除筛选
        </Button>
      </Box>
    </Paper>
  );
}

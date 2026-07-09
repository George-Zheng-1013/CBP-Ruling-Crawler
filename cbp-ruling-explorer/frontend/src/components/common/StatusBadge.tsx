import { Chip } from '@mui/material';
import { STATUS_COLORS } from '../../theme/theme';
import { statusLabel } from '../../utils/format';

interface Props {
  status: string;
  size?: 'small' | 'medium';
}

export function StatusBadge({ status, size = 'small' }: Props) {
  const color = STATUS_COLORS[status] ?? '#757575';
  return (
    <Chip
      label={statusLabel(status)}
      size={size}
      sx={{ backgroundColor: color, color: '#fff', fontWeight: 600 }}
    />
  );
}

import { STATUS_COLORS } from '../../theme/theme';
import { statusLabel } from '../../utils/format';

interface Props {
  status: string;
  size?: 'small' | 'medium';
}

export function StatusBadge({ status, size = 'small' }: Props) {
  const color = STATUS_COLORS[status] ?? '#757575';
  return (
    <span
      className={`chip chip-solid ${size === 'medium' ? 'text-xs px-2.5 py-1' : 'text-[11px] px-2 py-0.5'}`}
      style={{ backgroundColor: color }}
    >
      {statusLabel(status)}
    </span>
  );
}

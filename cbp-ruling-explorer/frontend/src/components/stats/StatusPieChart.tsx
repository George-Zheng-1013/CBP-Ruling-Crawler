import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { StatusCountFE } from '../../types/ruling';
import { STATUS_COLORS } from '../../theme/theme';

interface Props {
  data: StatusCountFE[];
}
const STATUS_LABELS: Record<string, string> = {
  active: '有效',
  revoked: '已撤销',
  modified: '已修改',
};

export function StatusPieChart({ data }: Props) {
  const localized = data.map((item) => ({
    ...item,
    label: STATUS_LABELS[item.status] ?? item.status,
  }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={localized}
          dataKey="count"
          nameKey="label"
          outerRadius={100}
          label
        >
          {data.map((entry) => (
            <Cell
              key={entry.status}
              fill={STATUS_COLORS[entry.status] ?? '#757575'}
            />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

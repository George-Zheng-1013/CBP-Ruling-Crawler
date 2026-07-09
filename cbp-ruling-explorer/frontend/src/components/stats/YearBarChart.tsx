import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { YearCountFE } from '../../types/ruling';
import { theme } from '../../theme/theme';

interface Props {
  data: YearCountFE[];
}

export function YearBarChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="year" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" name="裁定数" fill={theme.palette.primary.main} />
      </BarChart>
    </ResponsiveContainer>
  );
}

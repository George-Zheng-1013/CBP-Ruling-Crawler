import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ChapterCountFE } from '../../types/ruling';

interface Props {
  data: ChapterCountFE[];
}

export function ChapterBarChart({ data }: Props) {
  const top = data.slice(0, 20).map((item) => ({
    ...item,
    label: `CH ${item.chapter}`,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(360, top.length * 28)}>
      <BarChart data={top} layout="vertical" margin={{ left: 8, right: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e5ea" />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
        <YAxis
          type="category"
          dataKey="label"
          width={58}
          tick={{ fontSize: 12 }}
        />
        <Tooltip />
        <Bar
          dataKey="count"
          name="案例数"
          fill="#1a3e72"
          radius={[0, 4, 4, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

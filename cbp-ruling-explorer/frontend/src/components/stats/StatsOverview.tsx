import { StatsOverviewFE } from '../../types/ruling';
import { YearBarChart } from './YearBarChart';
import { StatusPieChart } from './StatusPieChart';

interface Props {
  stats: StatsOverviewFE;
}

export function StatsOverview({ stats }: Props) {
  const cards = [
    { value: stats.total.toLocaleString(), label: '裁定总数', color: 'text-navy' },
    { value: stats.parseFailed.toLocaleString(), label: '解析失败数', color: 'text-red-700' },
    { value: stats.byYear.length, label: '覆盖年份', color: '' },
    { value: stats.byStatus.length, label: '状态种类', color: '' },
  ];

  return (
    <div>
      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {cards.map((c) => (
          <div key={c.label} className="card p-4 text-center">
            <p className={`text-2xl font-bold ${c.color || 'text-gray-900'}`}>
              {c.value}
            </p>
            <p className="caption mt-1">{c.label}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
        <div className="card p-4 md:col-span-4">
          <h3 className="subheading mb-2">按年份分布</h3>
          <YearBarChart data={stats.byYear} />
        </div>
        <div className="card p-4 md:col-span-3">
          <h3 className="subheading mb-2">按状态分布</h3>
          <StatusPieChart data={stats.byStatus} />
        </div>
      </div>
    </div>
  );
}

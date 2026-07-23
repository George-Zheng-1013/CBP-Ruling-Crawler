import { StatsOverviewFE } from '../../types/ruling';
import { ChapterBarChart } from './ChapterBarChart';
import { StatusPieChart } from './StatusPieChart';
import { YearBarChart } from './YearBarChart';

interface Props {
  stats: StatsOverviewFE;
}

export function StatsOverview({ stats }: Props) {
  const cards = [
    { value: stats.total.toLocaleString(), label: '裁定总数', color: 'text-navy' },
    { value: stats.parseFailed.toLocaleString(), label: '解析失败数', color: 'text-red-700' },
    { value: stats.byYear.length, label: '覆盖年份', color: '' },
    { value: stats.byStatus.length, label: '状态种类', color: '' },
    { value: stats.byChapter.length, label: 'HTS Chapter 数量', color: '' },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {cards.map((card) => (
          <div key={card.label} className="card p-4 text-center">
            <p className={`text-2xl font-bold ${card.color || 'text-gray-900'}`}>
              {card.value}
            </p>
            <p className="caption mt-1">{card.label}</p>
          </div>
        ))}
      </div>

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

      <div className="card p-4 mt-4">
        <h3 className="subheading">CH 归类分布（前 20）</h3>
        <p className="caption mt-1 mb-3">
          按案例主 HTSUS 税号的前两位统计，每条案例只计入一个 Chapter。
        </p>
        <ChapterBarChart data={stats.byChapter} />
      </div>
    </div>
  );
}

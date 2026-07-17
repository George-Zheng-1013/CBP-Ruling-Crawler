import { RulingItemFE } from '../../types/ruling';
import { RulingCard } from './RulingCard';
import { Loading } from '../common/Loading';
import { ErrorState } from '../common/ErrorBoundary';

interface Props {
  items: RulingItemFE[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function ResultList({ items, loading, error, onRetry }: Props) {
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="heading text-muted mb-1">未找到匹配的裁定</p>
        <p className="caption">试试调整关键词或筛选条件</p>
      </div>
    );
  }
  return (
    <div className="columns-1 sm:columns-2 lg:columns-3 gap-3 space-y-3">
      {items.map((r) => (
        <RulingCard ruling={r} key={r.rulingNo} />
      ))}
    </div>
  );
}

import { useNavigate } from 'react-router-dom';
import { RulingItemFE } from '../../types/ruling';
import { StatusBadge } from '../common/StatusBadge';
import { useFavorites } from '../../store/favorites';
import { getChapterLabel } from '../../utils/htsChapters';

interface Props {
  ruling: RulingItemFE;
}

export function RulingCard({ ruling }: Props) {
  const navigate = useNavigate();
  const toggle = useFavorites((s) => s.toggle);
  const isFav = useFavorites((s) => s.favorites.includes(ruling.rulingNo));
  const chapterLabel = getChapterLabel(ruling.hsCodes);
  const hsCodes = ruling.hsCodes?.filter(Boolean) || [];

  return (
    <div className="card card-interactive mb-3 break-inside-avoid relative">
      {/* Favorite button */}
      <button
        className="absolute top-2 right-2 p-1.5 rounded-full hover:bg-black/5 transition z-10"
        onClick={(e) => {
          e.stopPropagation();
          toggle(ruling.rulingNo);
        }}
        aria-label={isFav ? '取消收藏' : '收藏'}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill={isFav ? '#ED6C02' : 'none'}
          stroke={isFav ? '#ED6C02' : '#86868b'}
          strokeWidth="2"
        >
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      </button>

      {/* Clickable body */}
      <button
        className="text-left w-full p-3 cursor-pointer block"
        onClick={() => navigate(`/ruling/${encodeURIComponent(ruling.rulingNo)}`)}
      >
        <p className="mono text-navy font-bold text-sm">{ruling.rulingNo}</p>
        <p className="subheading line-clamp-3 mt-1">{ruling.subject || '(无主题)'}</p>
        <div className="flex gap-2 items-center mt-2 flex-wrap">
          <span className="caption">{ruling.year || '—'}</span>
          <span className="caption">·</span>
          <StatusBadge status={ruling.status} />
          {ruling.parseFailed && (
            <span className="text-xs text-red-700 font-bold">解析失败</span>
          )}
        </div>
        {hsCodes.length > 0 && (
          <div className="flex gap-1 flex-wrap mt-2">
            {chapterLabel && (
              <span className="chip chip-accent text-xs">{chapterLabel}</span>
            )}
            {hsCodes.map((code) => (
              <span key={code} className="chip text-xs font-mono">{code}</span>
            ))}
          </div>
        )}
      </button>
    </div>
  );
}

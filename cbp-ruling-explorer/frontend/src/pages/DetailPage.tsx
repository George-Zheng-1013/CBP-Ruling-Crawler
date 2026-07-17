import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getRulingDetail } from '../api/rulings';
import { RulingDetailFE } from '../types/ruling';
import { DetailView } from '../components/detail/DetailView';
import { Loading } from '../components/common/Loading';
import { ErrorState } from '../components/common/ErrorBoundary';

export function DetailPage() {
  const { rulingNo } = useParams<{ rulingNo: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<RulingDetailFE | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!rulingNo) return;
    let active = true;
    setLoading(true);
    setError(null);
    getRulingDetail(rulingNo)
      .then((res) => active && setDetail(res))
      .catch((err: Error) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [rulingNo]);

  return (
    <div>
      <button
        className="btn btn-ghost mb-3 text-sm"
        onClick={() => navigate(-1)}
      >
        ← 返回
      </button>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={() => navigate(0)} />
      ) : detail ? (
        <DetailView ruling={detail} />
      ) : null}
    </div>
  );
}

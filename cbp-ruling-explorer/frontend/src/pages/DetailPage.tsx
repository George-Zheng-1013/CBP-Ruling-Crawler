import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Box, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { getRulingDetail, getRulingHtml } from '../api/rulings';
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
  const [htmlUrl, setHtmlUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!rulingNo) return;
    let active = true;
    setLoading(true);
    setError(null);
    setHtmlUrl(null);
    getRulingDetail(rulingNo)
      .then((res) => active && setDetail(res))
      .catch((err: Error) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [rulingNo]);

  const viewHtml = async () => {
    if (!rulingNo) return;
    try {
      const res = await getRulingHtml(rulingNo);
      const blob = new Blob([res.htmlContent || res.plainText], {
        type: 'text/html',
      });
      setHtmlUrl(URL.createObjectURL(blob));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate(-1)}
        sx={{ mb: 2 }}
      >
        返回
      </Button>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={() => navigate(0)} />
      ) : detail ? (
        <>
          <DetailView ruling={detail} onViewHtml={viewHtml} />
          {htmlUrl && (
            <Box sx={{ mt: 2 }}>
              <iframe
                title="raw-html"
                src={htmlUrl}
                sandbox="allow-same-origin"
                style={{ width: '100%', height: 600, border: '1px solid #ddd' }}
              />
            </Box>
          )}
        </>
      ) : null}
    </Box>
  );
}

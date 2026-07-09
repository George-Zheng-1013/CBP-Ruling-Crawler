import {
  Card,
  CardActionArea,
  CardContent,
  Box,
  Typography,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import StarIcon from '@mui/icons-material/Star';
import StarBorderIcon from '@mui/icons-material/StarBorder';
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
    <Card elevation={1} sx={{ position: 'relative', breakInside: 'avoid', mb: 2 }}>
      <CardActionArea
        onClick={() => navigate(`/ruling/${encodeURIComponent(ruling.rulingNo)}`)}
      >
        <CardContent>
          <Typography
            variant="body2"
            sx={{ fontFamily: 'monospace', color: 'primary.main', fontWeight: 700 }}
          >
            {ruling.rulingNo}
          </Typography>
          <Typography
            variant="subtitle1"
            sx={{
              fontWeight: 600,
              mt: 0.5,
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {ruling.subject || '(无主题)'}
          </Typography>
          <Box
            sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1, flexWrap: 'wrap' }}
          >
            <Typography variant="caption" color="text.secondary">
              {ruling.year || '—'}
            </Typography>
            <Typography variant="caption" color="text.secondary">·</Typography>
            <StatusBadge status={ruling.status} />
            {ruling.parseFailed && (
              <Typography variant="caption" sx={{ color: 'error.main', fontWeight: 700 }}>
                解析失败
              </Typography>
            )}
          </Box>
          {hsCodes.length > 0 && (
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1.5 }}>
              {chapterLabel && (
                <Chip label={chapterLabel} size="small" color="primary" variant="outlined" sx={{ fontWeight: 500 }} />
              )}
              {hsCodes.map((code) => (
                <Chip key={code} label={code} size="small" variant="outlined" sx={{ fontFamily: 'monospace' }} />
              ))}
            </Box>
          )}
        </CardContent>
      </CardActionArea>
      <Tooltip title={isFav ? '取消收藏' : '收藏'}>
        <IconButton
          size="small"
          sx={{ position: 'absolute', top: 8, right: 8 }}
          onClick={() => toggle(ruling.rulingNo)}
        >
          {isFav ? <StarIcon color="warning" /> : <StarBorderIcon />}
        </IconButton>
      </Tooltip>
    </Card>
  );
}

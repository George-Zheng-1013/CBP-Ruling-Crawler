import {
  Card,
  CardActionArea,
  CardContent,
  Box,
  Typography,
  IconButton,
  Tooltip,
} from '@mui/material';
import StarIcon from '@mui/icons-material/Star';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import { useNavigate } from 'react-router-dom';
import { RulingItemFE } from '../../types/ruling';
import { StatusBadge } from '../common/StatusBadge';
import { useFavorites } from '../../store/favorites';

interface Props {
  ruling: RulingItemFE;
}

export function RulingCard({ ruling }: Props) {
  const navigate = useNavigate();
  const toggle = useFavorites((s) => s.toggle);
  const isFav = useFavorites((s) => s.favorites.includes(ruling.rulingNo));

  return (
    <Card elevation={1} sx={{ position: 'relative' }}>
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
              WebkitLineClamp: 2,
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
            <Typography variant="caption" color="text.secondary">
              ·
            </Typography>
            <Typography variant="caption" color="text.secondary">
              HS {ruling.hsCode || '—'}
            </Typography>
            <StatusBadge status={ruling.status} />
            {ruling.parseFailed && (
              <Typography variant="caption" sx={{ color: 'error.main', fontWeight: 700 }}>
                解析失败
              </Typography>
            )}
          </Box>
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

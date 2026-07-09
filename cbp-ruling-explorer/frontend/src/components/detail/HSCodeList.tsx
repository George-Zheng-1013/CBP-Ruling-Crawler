import { Box, Chip, Typography } from '@mui/material';
import { getChapterNum } from '../../utils/htsChapters';

interface Props {
  mainHsCode: string;
  hsCodes: string[];
}

export function HSCodeList({ mainHsCode, hsCodes }: Props) {
  const all = mainHsCode
    ? [mainHsCode, ...hsCodes.filter((c) => c !== mainHsCode)]
    : hsCodes;
  const unique = Array.from(new Set(all.filter(Boolean)));
  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        HS Code
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {unique.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            —
          </Typography>
        ) : (
          unique.map((c) => {
            const ch = getChapterNum(c);
            const label = ch ? `${c}  · CH${ch}` : c;
            return <Chip key={c} label={label} size="small" variant="outlined" />;
          })
        )}
      </Box>
    </Box>
  );
}

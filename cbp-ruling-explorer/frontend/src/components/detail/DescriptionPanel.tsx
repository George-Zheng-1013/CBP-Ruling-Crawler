import { Box, Paper, Typography } from '@mui/material';

interface Props {
  text: string;
}

export function DescriptionPanel({ text }: Props) {
  return (
    <Paper
      sx={{ p: 2, mt: 2, maxHeight: 420, overflow: 'auto', whiteSpace: 'pre-wrap' }}
      elevation={1}
    >
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        全文描述
      </Typography>
      <Typography variant="body2" component="div" sx={{ lineHeight: 1.7 }}>
        {text || '（无内容）'}
      </Typography>
    </Paper>
  );
}

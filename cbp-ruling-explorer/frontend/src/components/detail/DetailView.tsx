import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useState } from 'react';
import { RulingDetailFE } from '../../types/ruling';
import { StatusBadge } from '../common/StatusBadge';
import { DescriptionPanel } from './DescriptionPanel';
import { HSCodeList } from './HSCodeList';
import { ParseFailedBadge } from './ParseFailedBadge';
import { formatDate, formatYear } from '../../utils/format';

interface Props {
  ruling: RulingDetailFE;
}

export function DetailView({ ruling }: Props) {
  const [copied, setCopied] = useState(false);

  const copyNo = async () => {
    try {
      await navigator.clipboard.writeText(ruling.rulingNo);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 剪贴板不可用时静默忽略。
    }
  };

  return (
    <Paper sx={{ p: 3 }} elevation={1}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="flex-start"
        flexWrap="wrap"
        gap={1}
      >
        <Box>
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              color: 'primary.main',
              fontWeight: 700,
              fontSize: 18,
            }}
          >
            {ruling.rulingNo}
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, mt: 0.5 }}>
            {ruling.subject || '(无主题)'}
          </Typography>
        </Box>
        <StatusBadge status={ruling.status} size="medium" />
      </Stack>

      <Box
        sx={{
          display: 'flex',
          gap: 3,
          mt: 2,
          flexWrap: 'wrap',
          color: 'text.secondary',
        }}
      >
        <Typography variant="body2">年份：{formatYear(ruling.year)}</Typography>
        <Typography variant="body2">
          裁定日期：{formatDate(ruling.rulingDate)}
        </Typography>
        <Typography variant="body2">状态：{ruling.status}</Typography>
      </Box>

      <HSCodeList mainHsCode={ruling.hsCode} hsCodes={ruling.hsCodes} />

      {ruling.parseFailed && <ParseFailedBadge message={ruling.parseErrorMsg} />}

      <DescriptionPanel text={ruling.description} />

      <Stack direction="row" spacing={2} sx={{ mt: 3 }} flexWrap="wrap">
        {ruling.detailUrl && (
          <Button
            variant="contained"
            startIcon={<OpenInNewIcon />}
            href={ruling.detailUrl}
            target="_blank"
            rel="noreferrer"
          >
            打开官方链接
          </Button>
        )}
        <Button
          variant="outlined"
          startIcon={<ContentCopyIcon />}
          onClick={copyNo}
        >
          {copied ? '已复制' : '复制编号'}
        </Button>
      </Stack>
    </Paper>
  );
}

import { Alert } from '@mui/material';

interface Props {
  message: string;
}

export function ParseFailedBadge({ message }: Props) {
  return (
    <Alert severity="error" sx={{ mt: 2 }}>
      <strong>解析失败</strong>
      {message
        ? `：${message}`
        : '，该裁定内容解析时出错，部分字段可能缺失。'}
    </Alert>
  );
}

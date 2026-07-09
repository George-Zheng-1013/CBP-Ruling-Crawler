import { useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material';

interface CrawlDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (minDate: string) => void;
}

export function CrawlDialog({ open, onClose, onConfirm }: CrawlDialogProps) {
  const today = new Date().toISOString().slice(0, 10);
  const defaultDate = '2025-01-01';
  const [minDate, setMinDate] = useState(defaultDate);

  const handleConfirm = () => {
    if (minDate) onConfirm(minDate);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>全库数据同步</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          指定起始日期，从该日期起检查并同步所有 HQ/NY/N 系列裁定
          （更新已有记录 + 新增裁定，不会清空已有数据）。
        </Typography>
        <TextField
          label="起始日期 (min_date)"
          type="date"
          value={minDate}
          onChange={(e) => setMinDate(e.target.value)}
          fullWidth
          InputLabelProps={{ shrink: true }}
          inputProps={{ min: '2000-01-01', max: today }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">取消</Button>
        <Button onClick={handleConfirm} variant="contained" disabled={!minDate}>
          开始同步
        </Button>
      </DialogActions>
    </Dialog>
  );
}

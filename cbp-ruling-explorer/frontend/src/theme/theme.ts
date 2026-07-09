import { createTheme } from '@mui/material/styles';

// 海关深蓝主色，呼应 CBP 官方气质。
export const theme = createTheme({
  palette: {
    primary: { main: '#1A3E72' },
    secondary: { main: '#2E6FB0' },
    background: { default: '#F5F7FA', paper: '#FFFFFF' },
    success: { main: '#2E7D32' },
    error: { main: '#C62828' },
    warning: { main: '#ED6C02' },
  },
  typography: {
    fontFamily: 'Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  shape: { borderRadius: 8 },
});

// 状态色标：用于 StatusBadge / 统计饼图。
export const STATUS_COLORS: Record<string, string> = {
  active: '#2E7D32',
  revoked: '#C62828',
  modified: '#ED6C02',
  third_party: '#757575',
};

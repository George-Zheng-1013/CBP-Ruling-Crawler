import { Alert, AlertTitle, Box } from '@mui/material';
import { Component, ErrorInfo, ReactNode } from 'react';

interface BoundaryProps {
  children: ReactNode;
}
interface BoundaryState {
  hasError: boolean;
  message: string;
}

/** 渲染期错误的错误边界。 */
export class ErrorBoundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): BoundaryState {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ p: 3 }}>
          <Alert severity="error">
            <AlertTitle>出错了</AlertTitle>
            {this.state.message}
          </Alert>
        </Box>
      );
    }
    return this.props.children;
  }
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

/** 获取失败时的错误提示（可点击重试）。 */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Alert
      severity="error"
      action={
        onRetry ? (
          <Box
            component="span"
            onClick={onRetry}
            sx={{ cursor: 'pointer', fontWeight: 600 }}
          >
            重试
          </Box>
        ) : undefined
      }
    >
      {message}
    </Alert>
  );
}

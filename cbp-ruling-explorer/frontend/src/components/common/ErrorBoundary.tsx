import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorState message={this.state.message} />;
    }
    return this.props.children;
  }
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="p-4 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
      <p className="font-semibold mb-1">出错了</p>
      <p>{message}</p>
      {onRetry && (
        <button
          className="mt-2 text-red-700 font-semibold underline cursor-pointer hover:opacity-80"
          onClick={onRetry}
        >
          重试
        </button>
      )}
    </div>
  );
}

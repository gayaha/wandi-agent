import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('App error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          dir="rtl"
          className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground gap-4 p-6"
        >
          <p className="text-xl font-semibold text-center">
            אופס, משהו השתבש
          </p>
          <p className="text-muted-foreground text-center max-w-md">
            קרתה שגיאה לא צפויה. לחצי על הכפתור למטה כדי לרענן את הדף.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
          >
            רענון העמוד
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

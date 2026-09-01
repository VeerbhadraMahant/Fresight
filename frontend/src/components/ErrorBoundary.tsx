import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
}

/** Keeps one broken panel from blanking the whole dashboard. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("FreightSight render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="shell py-16">
          <div className="border border-graphite bg-canvas p-10">
            <h1 className="h-section">Something broke while rendering.</h1>
            <p className="caption mt-3 max-w-2xl">{this.state.error.message}</p>
            <button
              type="button"
              className="btn-primary mt-6"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

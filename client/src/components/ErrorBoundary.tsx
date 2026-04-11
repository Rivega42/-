import { Component, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-8">
          <AlertTriangle className="w-20 h-20 text-red-500 mb-6" />
          <h2 className="text-2xl font-bold text-slate-800 mb-3">Произошла ошибка</h2>
          <p className="text-slate-500 mb-6 text-center max-w-md">
            {this.state.error?.message || "Неизвестная ошибка интерфейса"}
          </p>
          <Button
            size="lg"
            variant="destructive"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = "/";
            }}
          >
            Перезагрузить
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

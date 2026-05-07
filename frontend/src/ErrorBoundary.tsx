import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
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

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="boot-screen">
          <main className="boot-card">
            <p className="eyebrow">Kongming Agent</p>
            <h1>孔明暂不能应答</h1>
            <p>页面遇到了意外错误，请刷新后重试。</p>
            {this.state.error && (
              <details style={{ marginTop: 16, textAlign: 'left' }}>
                <summary style={{ cursor: 'pointer', color: '#d7b46c' }}>查看错误详情</summary>
                <pre style={{ marginTop: 8, fontSize: 12, color: '#b5bfd2', whiteSpace: 'pre-wrap' }}>
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <button
              style={{
                marginTop: 20,
                padding: '11px 20px',
                borderRadius: 14,
                border: '1px solid rgba(255,255,255,0.14)',
                background: 'transparent',
                color: '#f4efe6',
                cursor: 'pointer',
              }}
              onClick={() => window.location.reload()}
            >
              刷新页面
            </button>
          </main>
        </div>
      );
    }
    return this.props.children;
  }
}

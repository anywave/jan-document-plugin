/**
 * Error Boundary for Document RAG components.
 * Catches render errors and offers a retry with ChromaDB health check.
 */

import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { checkChromaDbHealth } from '../python-bridge'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  recovering: boolean
  recoveryResult: string | null
}

export class DocumentRAGErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      recovering: false,
      recoveryResult: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[DocumentRAG] Error caught by boundary:', error, errorInfo)
  }

  handleRetry = async () => {
    this.setState({ recovering: true, recoveryResult: null })

    try {
      const health = await checkChromaDbHealth('documents', true)
      if (health.healthy) {
        this.setState({
          hasError: false,
          error: null,
          recovering: false,
          recoveryResult: health.recovered
            ? 'Database recovered. Retrying...'
            : 'Database is healthy. Retrying...',
        })
      } else {
        this.setState({
          recovering: false,
          recoveryResult: `Health check failed: ${health.error || 'Unknown error'}`,
        })
      }
    } catch (err) {
      this.setState({
        recovering: false,
        recoveryResult: `Recovery error: ${String(err)}`,
      })
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 rounded-lg border border-destructive/50 bg-destructive/10">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
            <div className="space-y-3 flex-1">
              <h3 className="font-semibold text-destructive">
                Document RAG Error
              </h3>
              <p className="text-sm text-destructive/90">
                {this.state.error?.message || 'An unexpected error occurred.'}
              </p>
              {this.state.recoveryResult && (
                <p className="text-sm text-muted-fg">{this.state.recoveryResult}</p>
              )}
              <button
                onClick={this.handleRetry}
                disabled={this.state.recovering}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-fg rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <RefreshCw
                  className={`h-4 w-4 ${this.state.recovering ? 'animate-spin' : ''}`}
                />
                {this.state.recovering ? 'Checking...' : 'Retry with Health Check'}
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

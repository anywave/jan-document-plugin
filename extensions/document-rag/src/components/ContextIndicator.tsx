/**
 * Context Indicator
 * Shows active document context in chat
 */

import React from 'react'
import { FileText, X } from 'lucide-react'
import { useDocumentContext } from '../hooks/useDocumentContext'
import { cn } from '@/lib/utils'

interface ContextIndicatorProps {
  /** Current thread ID */
  threadId: string
  /** Optional className */
  className?: string
}

export const ContextIndicator: React.FC<ContextIndicatorProps> = ({
  threadId,
  className,
}) => {
  const { getContext, clearContext } = useDocumentContext()
  const context = getContext(threadId)
  const [isExpanded, setIsExpanded] = React.useState(false)

  if (context.length === 0) return null

  // Count unique sources
  const uniqueSources = Array.from(new Set(context.map((c) => c.source)))

  return (
    <div
      className={cn(
        'border border-border rounded-lg bg-accent/50 overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-2 bg-accent/30">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm text-fg hover:text-primary transition-colors flex-1"
        >
          <FileText className="w-4 h-4 text-primary" />
          <span className="font-medium">
            {context.length} document chunk{context.length !== 1 ? 's' : ''}{' '}
            from {uniqueSources.length} source{uniqueSources.length !== 1 ? 's' : ''}
          </span>
          <span className="text-xs text-muted-fg ml-auto mr-2">
            {isExpanded ? 'Hide' : 'Show'}
          </span>
        </button>
        <button
          onClick={() => clearContext(threadId)}
          className="p-1 rounded-md hover:bg-destructive/10 hover:text-destructive transition-colors"
          title="Clear context"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Expanded view */}
      {isExpanded && (
        <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
          {context.map((item, index) => {
            const score = Math.round((1 - item.distance) * 100)
            return (
              <div
                key={index}
                className="p-2 bg-bg rounded border border-border text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-fg truncate flex-1">
                    {item.source}
                  </span>
                  <span
                    className={cn(
                      'text-xs px-1.5 py-0.5 rounded',
                      score >= 80
                        ? 'bg-green-500/20 text-green-700 dark:text-green-400'
                        : score >= 60
                          ? 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-400'
                          : 'bg-orange-500/20 text-orange-700 dark:text-orange-400'
                    )}
                  >
                    {score}%
                  </span>
                </div>
                <p className="text-muted-fg line-clamp-2">{item.content}</p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

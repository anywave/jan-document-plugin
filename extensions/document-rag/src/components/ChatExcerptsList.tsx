import React, { useState, useMemo } from 'react'
import { MessageSquare, ChevronDown, ChevronRight, Trash2, Plus } from 'lucide-react'
import { useChatExcerpts, type ChatExcerpt } from '@/hooks/useChatExcerpts'
import { useDocumentContext } from '../hooks/useDocumentContext'
import { useThreads } from '@/hooks/useThreads'
import { toast } from 'sonner'

export function ChatExcerptsList() {
  const { excerpts, removeExcerpt } = useChatExcerpts()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const { currentThreadId } = useThreads()
  const { addToContext } = useDocumentContext()

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleAddToContext = () => {
    if (!currentThreadId) {
      toast.error('No active chat thread. Start a conversation first.')
      return
    }
    if (selectedIds.size === 0) {
      toast.info('No excerpts selected.')
      return
    }

    const selected = excerpts.filter((e) => selectedIds.has(e.id))
    const contextItems = selected.map((excerpt) => ({
      source: `Chat excerpt: ${excerpt.assistantName}`,
      content: excerpt.highlightText,
      distance: 0,
      metadata: {
        assistant: excerpt.assistantName,
        timestamp: excerpt.timestamp,
        inputPrompt: excerpt.inputPrompt,
      },
    }))

    addToContext(currentThreadId, contextItems)
    toast.success(
      `Added ${selectedIds.size} excerpt${selectedIds.size !== 1 ? 's' : ''} to chat context`
    )
    setSelectedIds(new Set())
  }

  if (excerpts.length === 0) {
    return (
      <div className="p-8 text-center space-y-3">
        <MessageSquare className="h-12 w-12 text-muted-fg/30 mx-auto" />
        <p className="text-sm text-muted-fg">No chat excerpts saved yet.</p>
        <p className="text-xs text-muted-fg/70">
          Highlight text in a conversation and right-click to save.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="text-sm text-muted-fg">
        {excerpts.length} excerpt{excerpts.length !== 1 ? 's' : ''}
      </div>

      <div className="border border-border rounded-lg divide-y divide-border">
        {excerpts.map((excerpt) => {
          const isExpanded = expandedId === excerpt.id
          const isSelected = selectedIds.has(excerpt.id)
          const date = new Date(excerpt.createdAt)
          const timeStr = date.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })

          return (
            <div key={excerpt.id}>
              <div
                className={`flex items-start gap-2 px-3 py-2 cursor-pointer transition-colors ${
                  isSelected ? 'bg-primary/5' : 'hover:bg-muted/30'
                }`}
              >
                {/* Checkbox */}
                <div
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleSelect(excerpt.id)
                  }}
                  className={`mt-1 shrink-0 h-4 w-4 rounded border flex items-center justify-center transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-primary border-primary'
                      : 'border-muted-fg/30'
                  }`}
                >
                  {isSelected && (
                    <svg
                      className="h-3 w-3 text-primary-fg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </div>

                {/* Content */}
                <div
                  className="flex-1 min-w-0"
                  onClick={() =>
                    setExpandedId(isExpanded ? null : excerpt.id)
                  }
                >
                  <p className="text-xs text-fg/80 leading-relaxed line-clamp-3">
                    {excerpt.highlightText}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">
                      {excerpt.assistantName}
                    </span>
                    <span className="text-[10px] text-muted-fg">{timeStr}</span>
                  </div>
                </div>

                {/* Expand toggle */}
                <div
                  className="shrink-0 mt-1 cursor-pointer text-muted-fg"
                  onClick={() =>
                    setExpandedId(isExpanded ? null : excerpt.id)
                  }
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>

                {/* Remove */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    removeExcerpt(excerpt.id)
                  }}
                  className="shrink-0 mt-1 p-0.5 rounded hover:bg-destructive/10 text-muted-fg hover:text-destructive transition-colors"
                  title="Remove excerpt"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="px-3 py-2 pl-9 bg-muted/10 border-t border-border/50 space-y-2">
                  {excerpt.inputPrompt && (
                    <div>
                      <span className="text-[10px] text-muted-fg font-medium uppercase tracking-wider">
                        In response to:
                      </span>
                      <p className="text-xs text-fg/70 mt-0.5 line-clamp-3">
                        {excerpt.inputPrompt}
                      </p>
                    </div>
                  )}
                  <div>
                    <span className="text-[10px] text-muted-fg font-medium uppercase tracking-wider">
                      Full message:
                    </span>
                    <p className="text-xs text-fg/70 mt-0.5 whitespace-pre-wrap max-h-48 overflow-auto">
                      {excerpt.fullMessage}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Action Bar */}
      {selectedIds.size > 0 && (
        <div className="sticky bottom-0 flex items-center justify-between p-3 bg-primary/10 border border-primary/20 rounded-lg">
          <span className="text-sm font-medium text-primary">
            {selectedIds.size} excerpt{selectedIds.size !== 1 ? 's' : ''}{' '}
            selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-xs text-muted-fg hover:text-fg transition-colors px-2 py-1"
            >
              Clear
            </button>
            <button
              onClick={handleAddToContext}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-fg text-sm font-medium rounded-md hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              Add to Chat Context
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

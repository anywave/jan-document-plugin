/**
 * Document Search Modal
 * Modal for searching documents within chat
 */

import React from 'react'
import { X } from 'lucide-react'
import { SearchInterface } from './SearchInterface'
import { QueryResult } from '../python-bridge'
import { useDocumentContext, DocumentContextItem } from '../hooks/useDocumentContext'
import { toast } from 'sonner'

interface DocumentSearchModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback when modal should close */
  onClose: () => void
  /** Current thread ID */
  threadId: string
  /** Collection name to search */
  collectionName?: string
}

export const DocumentSearchModal: React.FC<DocumentSearchModalProps> = ({
  isOpen,
  onClose,
  threadId,
  collectionName = 'documents',
}) => {
  const { addToContext } = useDocumentContext()

  if (!isOpen) return null

  const handleResultsFound = (results: QueryResult) => {
    // Convert query results to context items
    const contextItems: DocumentContextItem[] = results.results.map((r) => ({
      source: r.metadata?.source || 'Unknown',
      content: r.document,
      distance: r.distance,
      metadata: r.metadata,
    }))

    // Add to context
    addToContext(threadId, contextItems)

    // Show notification
    toast.success(
      `Added ${contextItems.length} document${contextItems.length !== 1 ? 's' : ''} to context`
    )

    // Close modal
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-bg border border-border rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-fg">Search Documents</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-accent transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-muted-fg" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          <SearchInterface
            collectionName={collectionName}
            onResultsFound={handleResultsFound}
          />
        </div>
      </div>
    </div>
  )
}

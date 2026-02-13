/**
 * Xtract Lib Component
 * Tree view of documents grouped by source file, with chunk selection
 * for deliberate context injection into chat.
 */

import React, { useState, useEffect, useMemo } from 'react'
import { ChevronRight, ChevronDown, FileText, Check, Plus, RefreshCw } from 'lucide-react'
import { listDocumentsBySource, type DocumentGroup, type DocumentChunk } from '../python-bridge'
import { useDocumentContext } from '../hooks/useDocumentContext'
import { useThreads } from '@/hooks/useThreads'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { ChatExcerptsList } from './ChatExcerptsList'

interface XtractLibProps {
  collectionName?: string
  className?: string
}

export function XtractLib({ collectionName = 'documents', className = '' }: XtractLibProps) {
  const [viewMode, setViewMode] = useState<'documents' | 'excerpts'>('documents')
  const [documents, setDocuments] = useState<DocumentGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set())
  const [selectedChunks, setSelectedChunks] = useState<Map<string, DocumentChunk>>(new Map())

  const { currentThreadId } = useThreads()
  const { addToContext } = useDocumentContext()

  const loadDocuments = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await listDocumentsBySource(collectionName)
      if (result.error) {
        setError(result.error)
      } else {
        setDocuments(result.documents)
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [collectionName])

  const toggleExpanded = (fileName: string) => {
    setExpandedDocs((prev) => {
      const next = new Set(prev)
      if (next.has(fileName)) next.delete(fileName)
      else next.add(fileName)
      return next
    })
  }

  const toggleChunk = (chunk: DocumentChunk) => {
    setSelectedChunks((prev) => {
      const next = new Map(prev)
      if (next.has(chunk.id)) next.delete(chunk.id)
      else next.set(chunk.id, chunk)
      return next
    })
  }

  const toggleAllChunksForDoc = (doc: DocumentGroup) => {
    setSelectedChunks((prev) => {
      const next = new Map(prev)
      const allSelected = doc.chunks.every((c) => next.has(c.id))
      if (allSelected) {
        doc.chunks.forEach((c) => next.delete(c.id))
      } else {
        doc.chunks.forEach((c) => next.set(c.id, c))
      }
      return next
    })
  }

  const handleAddToContext = () => {
    if (!currentThreadId) {
      toast.error('No active chat thread. Start a conversation first.')
      return
    }
    if (selectedChunks.size === 0) {
      toast.info('No chunks selected.')
      return
    }

    const contextItems = Array.from(selectedChunks.values()).map((chunk) => ({
      source: chunk.metadata?.file_name || 'Unknown',
      content: chunk.text,
      distance: 0,
      metadata: chunk.metadata,
    }))

    addToContext(currentThreadId, contextItems)
    toast.success(`Added ${selectedChunks.size} chunk${selectedChunks.size !== 1 ? 's' : ''} to chat context`)
    setSelectedChunks(new Map())
  }

  const totalChunks = useMemo(() => {
    return documents.reduce((sum, doc) => sum + doc.chunk_count, 0)
  }, [documents])

  const segmentedControl = (
    <div className="flex gap-1 bg-muted/20 rounded-md p-0.5 mb-3">
      <button
        onClick={() => setViewMode('documents')}
        className={cn(
          'px-3 py-1 text-xs rounded-sm transition-colors',
          viewMode === 'documents'
            ? 'bg-primary/20 text-primary font-medium'
            : 'text-muted-fg hover:text-fg'
        )}
      >
        Documents
      </button>
      <button
        onClick={() => setViewMode('excerpts')}
        className={cn(
          'px-3 py-1 text-xs rounded-sm transition-colors',
          viewMode === 'excerpts'
            ? 'bg-primary/20 text-primary font-medium'
            : 'text-muted-fg hover:text-fg'
        )}
      >
        Chat Excerpts
      </button>
    </div>
  )

  if (viewMode === 'excerpts') {
    return (
      <div className={`space-y-3 ${className}`}>
        {segmentedControl}
        <ChatExcerptsList />
      </div>
    )
  }

  if (loading) {
    return (
      <div className={`${className}`}>
        {segmentedControl}
        <div className="flex items-center justify-center p-12">
          <div className="text-center space-y-3">
            <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
            <p className="text-sm text-muted-fg">Loading document library...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`${className}`}>
        {segmentedControl}
        <div className="p-6 text-center space-y-3">
          <p className="text-sm text-destructive">{error}</p>
          <button
            onClick={loadDocuments}
            className="text-sm text-primary hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className={`${className}`}>
        {segmentedControl}
        <div className="p-8 text-center space-y-3">
          <FileText className="h-12 w-12 text-muted-fg/30 mx-auto" />
          <p className="text-sm text-muted-fg">No documents indexed yet.</p>
          <p className="text-xs text-muted-fg/70">Upload documents from the Upload tab to see them here.</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {segmentedControl}
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-fg">
          {documents.length} document{documents.length !== 1 ? 's' : ''} &middot; {totalChunks} chunks
        </div>
        <button
          onClick={loadDocuments}
          className="p-1.5 rounded hover:bg-muted/50 transition-colors"
          title="Refresh"
        >
          <RefreshCw className="h-4 w-4 text-muted-fg" />
        </button>
      </div>

      {/* Document Tree */}
      <div className="border border-border rounded-lg divide-y divide-border">
        {documents.map((doc) => {
          const isExpanded = expandedDocs.has(doc.file_name)
          const selectedCount = doc.chunks.filter((c) => selectedChunks.has(c.id)).length
          const allSelected = selectedCount === doc.chunk_count && doc.chunk_count > 0

          return (
            <div key={doc.file_name}>
              {/* Document Header (Level 1) */}
              <div
                className="flex items-center gap-2 px-3 py-2 hover:bg-muted/30 cursor-pointer transition-colors"
                onClick={() => toggleExpanded(doc.file_name)}
              >
                {isExpanded
                  ? <ChevronDown className="h-4 w-4 text-muted-fg shrink-0" />
                  : <ChevronRight className="h-4 w-4 text-muted-fg shrink-0" />
                }
                <FileText className="h-4 w-4 text-muted-fg shrink-0" />
                <span className="text-sm font-medium truncate flex-1">{doc.file_name}</span>
                <span className="text-xs text-muted-fg shrink-0">
                  {selectedCount > 0 && (
                    <span className="text-primary mr-2">{selectedCount} selected</span>
                  )}
                  {doc.chunk_count} chunk{doc.chunk_count !== 1 ? 's' : ''}
                </span>
                {/* Select All toggle for this document */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleAllChunksForDoc(doc)
                  }}
                  className={`p-1 rounded transition-colors shrink-0 ${
                    allSelected
                      ? 'bg-primary/20 text-primary'
                      : 'hover:bg-muted/50 text-muted-fg'
                  }`}
                  title={allSelected ? 'Deselect all' : 'Select all'}
                >
                  <Check className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* Chunks (Level 2) */}
              {isExpanded && (
                <div className="bg-muted/10">
                  {doc.chunks.map((chunk) => {
                    const isChunkSelected = selectedChunks.has(chunk.id)
                    const preview = chunk.text.slice(0, 200).replace(/\n/g, ' ')

                    return (
                      <div
                        key={chunk.id}
                        onClick={() => toggleChunk(chunk)}
                        className={`flex items-start gap-2 px-3 py-2 pl-10 cursor-pointer transition-colors border-t border-border/50 ${
                          isChunkSelected
                            ? 'bg-primary/5'
                            : 'hover:bg-muted/20'
                        }`}
                      >
                        <div className={`mt-0.5 shrink-0 h-4 w-4 rounded border flex items-center justify-center transition-colors ${
                          isChunkSelected
                            ? 'bg-primary border-primary'
                            : 'border-muted-fg/30'
                        }`}>
                          {isChunkSelected && <Check className="h-3 w-3 text-primary-fg" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-fg/80 leading-relaxed line-clamp-3">
                            {preview}{chunk.text.length > 200 ? '...' : ''}
                          </p>
                          {chunk.metadata?.chunk_index !== undefined && (
                            <span className="text-[10px] text-muted-fg mt-1 inline-block">
                              Chunk {chunk.metadata.chunk_index + 1}
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Action Bar */}
      {selectedChunks.size > 0 && (
        <div className="sticky bottom-0 flex items-center justify-between p-3 bg-primary/10 border border-primary/20 rounded-lg">
          <span className="text-sm font-medium text-primary">
            {selectedChunks.size} chunk{selectedChunks.size !== 1 ? 's' : ''} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedChunks(new Map())}
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

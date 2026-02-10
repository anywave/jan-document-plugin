/**
 * Document Library Component
 * Displays grid of uploaded documents with metadata
 */

import React, { useState, useEffect } from 'react'
import { FileText, File, Image, Trash2, Search } from 'lucide-react'
import { getCollectionStats, type CollectionStats } from '../python-bridge'
import { toast } from 'sonner'

interface Document {
  id: string
  name: string
  type: string
  uploadedAt?: string
  chunks?: number
}

interface DocumentLibraryProps {
  collectionName?: string
  onDocumentSelect?: (document: Document) => void
  className?: string
}

const getFileIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase()
  if (['pdf'].includes(ext || '')) return <FileText className="h-6 w-6" />
  if (['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'].includes(ext || ''))
    return <Image className="h-6 w-6" />
  return <File className="h-6 w-6" />
}

const getFileColor = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return 'text-red-500'
  if (['png', 'jpg', 'jpeg'].includes(ext || '')) return 'text-blue-500'
  if (['docx', 'doc'].includes(ext || '')) return 'text-blue-600'
  return 'text-muted-fg'
}

export function DocumentLibrary({
  collectionName = 'documents',
  onDocumentSelect,
  className = ''
}: DocumentLibraryProps) {
  const [stats, setStats] = useState<CollectionStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  const loadStats = async () => {
    try {
      setLoading(true)
      const result = await getCollectionStats(collectionName)
      setStats(result)
    } catch (error) {
      toast.error(`Failed to load documents: ${String(error)}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [collectionName])

  // Empty state
  if (!loading && (!stats || stats.document_count === 0)) {
    return (
      <div className={`flex flex-col items-center justify-center p-12 text-center ${className}`}>
        <FileText className="h-16 w-16 text-muted-fg mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Documents</h3>
        <p className="text-sm text-muted-fg max-w-sm">
          Upload documents to get started with RAG-powered search and Q&A
        </p>
      </div>
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <div className="h-4 w-32 bg-accent/20 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-4 rounded-lg border border-border bg-background">
              <div className="h-16 bg-accent/20 rounded animate-pulse mb-3" />
              <div className="h-4 w-3/4 bg-accent/20 rounded animate-pulse mb-2" />
              <div className="h-3 w-1/2 bg-accent/20 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Document Library</h3>
          <p className="text-sm text-muted-fg">
            {stats?.document_count || 0} document chunks indexed
          </p>
        </div>

        {/* Search Box */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-fg" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-3 py-2 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
      </div>

      {/* Collections Tabs */}
      {stats && stats.all_collections.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {stats.all_collections.map((collection) => (
            <button
              key={collection}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                collection === collectionName
                  ? 'bg-primary text-primary-fg'
                  : 'bg-accent hover:bg-accent/80 text-fg'
              }`}
            >
              {collection}
            </button>
          ))}
        </div>
      )}

      {/* Document Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Placeholder cards - in real implementation, query actual documents */}
        {[...Array(Math.min(stats?.document_count || 0, 12))].map((_, i) => (
          <DocumentCard
            key={i}
            document={{
              id: `doc-${i}`,
              name: `Document ${i + 1}.pdf`,
              type: 'pdf',
              uploadedAt: new Date().toISOString(),
              chunks: Math.floor(Math.random() * 50) + 10
            }}
            onSelect={onDocumentSelect}
          />
        ))}
      </div>

      {/* Show More Button */}
      {stats && stats.document_count > 12 && (
        <div className="flex justify-center pt-4">
          <button className="px-4 py-2 rounded-md border border-border hover:bg-accent transition-colors text-sm">
            Load More Documents
          </button>
        </div>
      )}
    </div>
  )
}

interface DocumentCardProps {
  document: Document
  onSelect?: (document: Document) => void
}

function DocumentCard({ document, onSelect }: DocumentCardProps) {
  const [showActions, setShowActions] = useState(false)

  return (
    <div
      className="group relative p-4 rounded-lg border border-border bg-background hover:border-primary/50 transition-all cursor-pointer"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      onClick={() => onSelect?.(document)}
    >
      {/* File Icon */}
      <div className={`mb-3 ${getFileColor(document.name)}`}>
        {getFileIcon(document.name)}
      </div>

      {/* File Name */}
      <h4 className="font-medium text-sm truncate mb-1">
        {document.name}
      </h4>

      {/* Metadata */}
      <div className="flex items-center gap-2 text-xs text-muted-fg">
        <span>{document.chunks || 0} chunks</span>
        {document.uploadedAt && (
          <>
            <span>•</span>
            <span>{new Date(document.uploadedAt).toLocaleDateString()}</span>
          </>
        )}
      </div>

      {/* Actions (on hover) */}
      {showActions && (
        <div className="absolute top-2 right-2 flex gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation()
              toast.error('Delete not implemented yet')
            }}
            className="p-1.5 rounded-md bg-background/80 backdrop-blur border border-border hover:bg-destructive hover:text-destructive-fg transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}

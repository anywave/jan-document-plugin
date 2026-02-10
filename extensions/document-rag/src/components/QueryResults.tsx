/**
 * Query Results Component
 * Displays search results with relevance scores and expandable content
 */

import React, { useState } from 'react'
import { FileText, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'
import { type QueryResult } from '../python-bridge'
import { toast } from 'sonner'

interface QueryResultsProps {
  results: QueryResult
  query: string
  className?: string
}

export function QueryResults({ results, query, className = '' }: QueryResultsProps) {
  if (results.error) {
    return (
      <div className={`p-4 rounded-lg border border-destructive/50 bg-destructive/10 ${className}`}>
        <p className="text-sm text-destructive">{results.error}</p>
      </div>
    )
  }

  if (results.results.length === 0) {
    return (
      <div className={`p-8 text-center rounded-lg border border-border bg-accent/30 ${className}`}>
        <FileText className="h-12 w-12 mx-auto text-muted-fg mb-3" />
        <h4 className="font-medium mb-1">No Results Found</h4>
        <p className="text-sm text-muted-fg">
          Try rephrasing your query or check if documents are indexed
        </p>
      </div>
    )
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Results Header */}
      <div className="flex items-center justify-between">
        <h4 className="font-medium">
          Found {results.results.length} result{results.results.length !== 1 ? 's' : ''}
        </h4>
        <span className="text-xs text-muted-fg">
          Sorted by relevance
        </span>
      </div>

      {/* Results List */}
      <div className="space-y-2">
        {results.results.map((result, index) => (
          <ResultCard
            key={result.id}
            result={result}
            rank={index + 1}
            query={query}
          />
        ))}
      </div>
    </div>
  )
}

interface ResultCardProps {
  result: {
    id: string
    text: string
    metadata: Record<string, any>
    distance: number
  }
  rank: number
  query: string
}

function ResultCard({ result, rank, query }: ResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  // Convert distance to similarity score (0-100%)
  const similarityScore = Math.round((1 - result.distance) * 100)

  // Get relevance color
  const getRelevanceColor = (score: number) => {
    if (score >= 80) return 'text-green-500'
    if (score >= 60) return 'text-yellow-500'
    return 'text-orange-500'
  }

  // Safely highlight query terms in text using React elements
  const highlightText = (text: string, query: string) => {
    if (!query) return <span>{text}</span>

    const words = query.toLowerCase().split(' ').filter(w => w.length > 2)
    if (words.length === 0) return <span>{text}</span>

    // Create regex pattern for all query words
    const pattern = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
    const regex = new RegExp(`(${pattern})`, 'gi')

    // Split text by matches
    const parts = text.split(regex)

    return (
      <>
        {parts.map((part, i) => {
          // Check if this part matches any query word
          const isMatch = words.some(word =>
            part.toLowerCase() === word.toLowerCase()
          )
          return isMatch ? (
            <mark key={i} className="bg-yellow-200/50 dark:bg-yellow-500/30 px-0.5">
              {part}
            </mark>
          ) : (
            <span key={i}>{part}</span>
          )
        })}
      </>
    )
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(result.text)
    setCopied(true)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  const displayText = expanded ? result.text : result.text.substring(0, 200)
  const needsTruncation = result.text.length > 200

  return (
    <div className="p-4 rounded-lg border border-border bg-background hover:border-primary/50 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          {/* Rank Badge */}
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-xs font-bold text-primary">{rank}</span>
          </div>

          {/* Source Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-muted-fg flex-shrink-0" />
              <span className="text-sm font-medium truncate">
                {result.metadata.file_name || 'Unknown Document'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-fg">
              <span className={getRelevanceColor(similarityScore)}>
                {similarityScore}% match
              </span>
              {result.metadata.chunk_index !== undefined && (
                <>
                  <span>•</span>
                  <span>Chunk {result.metadata.chunk_index + 1}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Copy Button */}
        <button
          onClick={copyToClipboard}
          className="p-1.5 rounded-md hover:bg-accent transition-colors"
          title="Copy text"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4 text-muted-fg" />
          )}
        </button>
      </div>

      {/* Text Content - Safe highlighting with React elements */}
      <div className="text-sm leading-relaxed mb-2">
        {highlightText(displayText, query)}
        {needsTruncation && !expanded && '...'}
      </div>

      {/* Expand Button */}
      {needsTruncation && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              Show more
            </>
          )}
        </button>
      )}

      {/* Metadata Footer */}
      {result.metadata.processed_at && (
        <div className="mt-3 pt-3 border-t border-border">
          <span className="text-xs text-muted-fg">
            Indexed: {new Date(result.metadata.processed_at).toLocaleString()}
          </span>
        </div>
      )}
    </div>
  )
}

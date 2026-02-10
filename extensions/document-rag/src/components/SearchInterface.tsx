/**
 * Search Interface Component
 * Allows users to query indexed documents with semantic search
 */

import React, { useState } from 'react'
import { Search, Loader2, SlidersHorizontal, X } from 'lucide-react'
import { queryDocuments, type QueryResult } from '../python-bridge'
import { QueryResults } from './QueryResults'
import { toast } from 'sonner'

interface SearchInterfaceProps {
  collectionName?: string
  className?: string
  /** Optional callback when results are found */
  onResultsFound?: (results: QueryResult) => void
}

export function SearchInterface({
  collectionName = 'documents',
  className = '',
  onResultsFound
}: SearchInterfaceProps) {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<QueryResult | null>(null)
  const [searching, setSearching] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [topK, setTopK] = useState(5)

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error('Please enter a search query')
      return
    }

    try {
      setSearching(true)
      setSearchResults(null)

      const result = await queryDocuments(query, {
        collectionName,
        topK
      })

      if (result.error) {
        toast.error(`Search failed: ${result.error}`)
      } else if (result.results.length === 0) {
        toast.info('No results found')
      } else if (onResultsFound) {
        // Callback mode: call handler and don't display results
        onResultsFound(result)
        return
      }

      setSearchResults(result)
    } catch (error) {
      toast.error(`Search error: ${String(error)}`)
    } finally {
      setSearching(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const clearSearch = () => {
    setQuery('')
    setSearchResults(null)
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search Header */}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Search Documents</h3>
        <p className="text-sm text-muted-fg">
          Ask questions or search across your indexed documents
        </p>
      </div>

      {/* Search Input */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-5 w-5 text-muted-fg" />
          <input
            type="text"
            placeholder="Ask a question or search for content..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={searching}
            className="w-full pl-10 pr-24 py-3 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <div className="absolute right-2 top-2 flex gap-2">
            {query && (
              <button
                onClick={clearSearch}
                className="p-1.5 rounded-md hover:bg-accent transition-colors"
                title="Clear search"
              >
                <X className="h-4 w-4 text-muted-fg" />
              </button>
            )}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`p-1.5 rounded-md transition-colors ${
                showAdvanced
                  ? 'bg-primary text-primary-fg'
                  : 'hover:bg-accent text-muted-fg'
              }`}
              title="Advanced options"
            >
              <SlidersHorizontal className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Advanced Options */}
        {showAdvanced && (
          <div className="p-4 rounded-lg border border-border bg-accent/50 space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center justify-between">
                <span>Number of Results</span>
                <span className="text-muted-fg">{topK}</span>
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-fg">
                <span>1</span>
                <span>20</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                Collection
              </label>
              <input
                type="text"
                value={collectionName}
                disabled
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm opacity-50"
              />
            </div>
          </div>
        )}

        {/* Search Button */}
        <button
          onClick={handleSearch}
          disabled={searching || !query.trim()}
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-fg rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {searching ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="h-5 w-5" />
              Search Documents
            </>
          )}
        </button>
      </div>

      {/* Results */}
      {searchResults && !searching && (
        <QueryResults results={searchResults} query={query} />
      )}

      {/* Search Tips */}
      {!searchResults && !searching && (
        <div className="p-4 rounded-lg border border-border bg-accent/30">
          <h4 className="text-sm font-medium mb-2">Search Tips</h4>
          <ul className="text-sm text-muted-fg space-y-1">
            <li>• Ask questions in natural language</li>
            <li>• Be specific for better results</li>
            <li>• Try different phrasings if no results found</li>
            <li>• Results ranked by semantic similarity</li>
          </ul>
        </div>
      )}
    </div>
  )
}

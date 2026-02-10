/**
 * TypeScript bindings for Python document processing bridge
 * @module extensions/document-rag/python-bridge
 */

import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'

/**
 * Python environment status
 */
export interface PythonStatus {
  available: boolean
  version: string | null
  script_path: string | null
  error: string | null
}

/**
 * Document processing result
 */
export interface DocumentProcessResult {
  success: boolean
  file_path: string
  chunks_created: number
  error: string | null
}

/**
 * Query match result
 */
export interface QueryMatch {
  id: string
  text: string
  metadata: Record<string, any>
  distance: number
}

/**
 * Query result
 */
export interface QueryResult {
  query: string
  results: QueryMatch[]
  error: string | null
}

/**
 * Collection statistics
 */
export interface CollectionStats {
  collection: string
  document_count: number
  all_collections: string[]
}

/**
 * Document processing progress event
 */
export interface ProcessingProgress {
  status: 'starting' | 'complete' | 'failed'
  file: string
  chunks?: number
  error?: string
}

/**
 * Check if Python is available and scripts are installed
 */
export async function checkPythonStatus(): Promise<PythonStatus> {
  return invoke<PythonStatus>('check_python_status')
}

/**
 * Process a document: extract, chunk, embed, and store
 *
 * @param filePath - Path to document file
 * @param options - Processing options
 * @returns Processing result
 */
export async function processDocument(
  filePath: string,
  options?: {
    collectionName?: string
    useOcr?: boolean
    password?: string
  }
): Promise<DocumentProcessResult> {
  return invoke<DocumentProcessResult>('process_document', {
    filePath,
    collectionName: options?.collectionName,
    useOcr: options?.useOcr,
    password: options?.password,
  })
}

/**
 * Query indexed documents
 *
 * @param query - Search query
 * @param options - Query options
 * @returns Query results
 */
export async function queryDocuments(
  query: string,
  options?: {
    collectionName?: string
    topK?: number
  }
): Promise<QueryResult> {
  return invoke<QueryResult>('query_documents', {
    query,
    collectionName: options?.collectionName,
    topK: options?.topK,
  })
}

/**
 * Get collection statistics
 *
 * @param collectionName - Collection name (default: "documents")
 * @returns Collection statistics
 */
export async function getCollectionStats(
  collectionName?: string
): Promise<CollectionStats> {
  return invoke<CollectionStats>('get_collection_stats', {
    collectionName,
  })
}

/**
 * Listen to document processing progress events
 *
 * @param callback - Callback function for progress updates
 * @returns Unlisten function
 */
export async function onProcessingProgress(
  callback: (progress: ProcessingProgress) => void
) {
  return listen<ProcessingProgress>('document-processing', (event) => {
    callback(event.payload)
  })
}

/**
 * Example usage:
 *
 * ```typescript
 * import { checkPythonStatus, processDocument, queryDocuments } from './python-bridge'
 *
 * // Check Python status
 * const status = await checkPythonStatus()
 * if (!status.available) {
 *   console.error('Python not available:', status.error)
 *   return
 * }
 *
 * // Listen to progress
 * const unlisten = await onProcessingProgress((progress) => {
 *   console.log('Progress:', progress.status, progress.file)
 * })
 *
 * // Process a document
 * const result = await processDocument('/path/to/document.pdf', {
 *   collectionName: 'my-docs',
 *   useOcr: true
 * })
 *
 * if (result.success) {
 *   console.log(`Processed ${result.chunks_created} chunks`)
 * } else {
 *   console.error('Processing failed:', result.error)
 * }
 *
 * // Query documents
 * const queryResult = await queryDocuments('machine learning', {
 *   topK: 5
 * })
 *
 * queryResult.results.forEach((match, i) => {
 *   console.log(`${i+1}. ${match.metadata.file_name} (distance: ${match.distance})`)
 *   console.log(`   ${match.text.substring(0, 100)}...`)
 * })
 *
 * // Get statistics
 * const stats = await getCollectionStats()
 * console.log(`Collection: ${stats.collection}`)
 * console.log(`Documents: ${stats.document_count}`)
 * console.log(`All collections: ${stats.all_collections.join(', ')}`)
 *
 * // Cleanup
 * unlisten()
 * ```
 */

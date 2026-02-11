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
 * ChromaDB health check result
 */
export interface ChromaDbHealth {
  healthy: boolean
  document_count: number
  error: string | null
  recovered: boolean
}

/**
 * Structured error event from Python bridge
 */
export interface PythonBridgeError {
  error_type: 'timeout' | 'spawn_error' | 'execution_error'
  message: string
  attempt: number
  max_attempts: number
}

/**
 * Jan lock status
 */
export interface JanLockStatus {
  jan_installed: boolean
  jan_version: string | null
  jan_install_path: string | null
  mobius_locked: boolean
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
 * Check ChromaDB health status
 *
 * @param collectionName - Collection to check
 * @param autoRecover - Whether to auto-recover corrupt database
 * @returns Health check result
 */
export async function checkChromaDbHealth(
  collectionName?: string,
  autoRecover?: boolean
): Promise<ChromaDbHealth> {
  return invoke<ChromaDbHealth>('check_chromadb_health', {
    collectionName,
    autoRecover,
  })
}

/**
 * Check Jan lock status
 *
 * @returns Jan lock status from Windows registry
 */
export async function checkJanLockStatus(): Promise<JanLockStatus> {
  return invoke<JanLockStatus>('check_jan_lock_status')
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
 * Listen to Python bridge error events
 *
 * @param callback - Callback function for error events
 * @returns Unlisten function
 */
export async function onPythonError(
  callback: (error: PythonBridgeError) => void
) {
  return listen<PythonBridgeError>('python-error', (event) => {
    callback(event.payload)
  })
}

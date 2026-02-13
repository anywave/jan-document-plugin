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
 * Rich document summary returned after processing
 */
export interface DocumentSummary {
  file_name: string
  file_size_bytes: number
  file_size_mb: number
  word_count: number
  char_count: number
  chunks_created: number
  sections_detected: string[]
  preview: string
  processing_time: number
}

/**
 * Document processing result
 */
export interface DocumentProcessResult {
  success: boolean
  file_path: string
  chunks_created: number
  error: string | null
  processing_time: number | null
  document_summary: DocumentSummary | null
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
 * A scanned file entry from directory scanning
 */
export interface ScannedFile {
  path: string
  name: string
  size: number
  extension: string
}

/**
 * Result of scanning a directory for processable files
 */
export interface ScanDirectoryResult {
  files: ScannedFile[]
  total_size: number
  skipped: number
}

/**
 * Per-file result emitted during batch processing (from stderr)
 */
export interface BatchFileResult {
  file_result: true
  file_path: string
  file_name: string
  success: boolean
  chunks_created: number
  error: string | null
  processing_time: number
  batch_index: number
  batch_total: number
}

/**
 * Aggregate result from batch processing
 */
export interface BatchProcessResult {
  results: DocumentProcessResult[]
  success_count: number
  error_count: number
  total_files: number
  total_time: number
}

/**
 * A chunk within a source document group
 */
export interface DocumentChunk {
  id: string
  text: string
  metadata: Record<string, any>
}

/**
 * A document group (source file with its chunks)
 */
export interface DocumentGroup {
  file_name: string
  chunk_count: number
  chunks: DocumentChunk[]
}

/**
 * Result of listing documents grouped by source
 */
export interface DocumentsBySourceResult {
  documents: DocumentGroup[]
  error: string | null
}

/**
 * Document processing progress event
 */
export interface ProcessingProgress {
  status?: 'starting' | 'complete' | 'failed'
  file?: string
  chunks?: number
  error?: string
  /** Granular progress from Python pipeline */
  progress?: boolean
  step?: number
  total_steps?: number
  step_name?: string
  detail?: string
  percent?: number
  /** Batch fields */
  batch_index?: number
  batch_total?: number
  success_count?: number
  error_count?: number
  total_time?: number
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
    smart?: boolean
  }
): Promise<DocumentProcessResult> {
  return invoke<DocumentProcessResult>('process_document', {
    filePath,
    collectionName: options?.collectionName,
    useOcr: options?.useOcr,
    password: options?.password,
    smart: options?.smart,
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

/**
 * Scan a directory for processable document files (pure Rust, instant)
 *
 * @param directoryPath - Path to directory to scan
 * @returns Scan results with file list, total size, and skipped count
 */
export async function scanDirectory(
  directoryPath: string
): Promise<ScanDirectoryResult> {
  return invoke<ScanDirectoryResult>('scan_directory', {
    directoryPath,
  })
}

/**
 * List all documents grouped by source file
 *
 * @param collectionName - Collection name (default: "documents")
 * @returns Documents grouped by source file with chunks
 */
export async function listDocumentsBySource(
  collectionName?: string
): Promise<DocumentsBySourceResult> {
  return invoke<DocumentsBySourceResult>('list_documents_by_source', {
    collectionName,
  })
}

/**
 * Process multiple documents in a single batch (model loaded once)
 *
 * @param filePaths - Array of file paths to process
 * @param options - Processing options
 * @returns Aggregate batch result
 */
export async function processDocumentBatch(
  filePaths: string[],
  options?: {
    collectionName?: string
    smart?: boolean
  }
): Promise<BatchProcessResult> {
  return invoke<BatchProcessResult>('process_document_batch', {
    filePaths,
    collectionName: options?.collectionName,
    smart: options?.smart,
  })
}

/**
 * Listen to per-file batch result events (emitted in real-time during batch)
 *
 * @param callback - Callback for each file result
 * @returns Unlisten function
 */
export async function onBatchFileResult(
  callback: (result: BatchFileResult) => void
) {
  return listen<BatchFileResult>('batch-file-result', (event) => {
    callback(event.payload)
  })
}

// --- Voice Relay ---

/**
 * Voice relay server status
 */
export interface VoiceRelayStatus {
  running: boolean
  url: string | null
  setup_url: string | null
  port: number
  error: string | null
}

/**
 * Start the voice relay server (phone-as-mic over Wi-Fi)
 */
export async function startVoiceRelay(
  port?: number
): Promise<VoiceRelayStatus> {
  return invoke<VoiceRelayStatus>('start_voice_relay', { port })
}

/**
 * Stop the voice relay server
 */
export async function stopVoiceRelay(): Promise<VoiceRelayStatus> {
  return invoke<VoiceRelayStatus>('stop_voice_relay')
}

/**
 * Get voice relay server status
 */
export async function getVoiceRelayStatus(): Promise<VoiceRelayStatus> {
  return invoke<VoiceRelayStatus>('get_voice_relay_status')
}

/**
 * Document Upload Component
 * Allows users to select and upload documents for RAG processing
 */

import React, { useState } from 'react'
import { FileText, Upload, X, AlertCircle } from 'lucide-react'
import { processDocument, onProcessingProgress, type ProcessingProgress } from '../python-bridge'
import { toast } from 'sonner'
import { open } from '@tauri-apps/plugin-dialog'

interface DocumentUploadProps {
  onUploadComplete?: (filePath: string, chunks: number) => void
  collectionName?: string
  className?: string
}

interface UploadingFile {
  path: string
  name: string
  status: 'uploading' | 'processing' | 'complete' | 'error'
  progress?: string
  chunksCreated?: number
  error?: string
}

const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.doc', '.docx']

export function DocumentUpload({
  onUploadComplete,
  collectionName = 'documents',
  className = ''
}: DocumentUploadProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])

  // Listen to processing progress events
  React.useEffect(() => {
    const setupListener = async () => {
      const unlisten = await onProcessingProgress((progress: ProcessingProgress) => {
        setUploadingFiles(prev => prev.map(file => {
          if (file.path === progress.file) {
            return {
              ...file,
              status: progress.status === 'complete' ? 'complete' :
                      progress.status === 'failed' ? 'error' : 'processing',
              progress: progress.status,
              chunksCreated: progress.chunks,
              error: progress.error
            }
          }
          return file
        }))
      })

      return unlisten
    }

    let unlistenFn: (() => void) | null = null
    setupListener().then(fn => { unlistenFn = fn })

    return () => {
      if (unlistenFn) unlistenFn()
    }
  }, [])

  const handleSelectFiles = async () => {
    try {
      const selected = await open({
        multiple: true,
        filters: [{ name: 'Documents', extensions: ['txt', 'md', 'doc', 'docx'] }],
      })
      if (!selected) return

      const paths = Array.isArray(selected) ? selected : [selected]

      // Add files to uploading list
      const newFiles: UploadingFile[] = paths.map(filePath => ({
        path: filePath,
        name: filePath.split(/[\\/]/).pop() || filePath,
        status: 'uploading' as const,
      }))

      setUploadingFiles(prev => [...prev, ...newFiles])

      // Process each file
      for (const filePath of paths) {
        const fileName = filePath.split(/[\\/]/).pop() || filePath

        try {
          const result = await processDocument(filePath, {
            collectionName,
            useOcr: true
          })

          if (result.success) {
            toast.success(`Processed ${fileName}: ${result.chunks_created} chunks`)
            onUploadComplete?.(result.file_path, result.chunks_created)
          } else {
            toast.error(`Failed to process ${fileName}: ${result.error}`)
          }

          setUploadingFiles(prev => prev.map(f =>
            f.path === filePath
              ? {
                  ...f,
                  status: result.success ? 'complete' : 'error',
                  chunksCreated: result.chunks_created,
                  error: result.error || undefined
                }
              : f
          ))
        } catch (error) {
          console.error(`Error processing ${fileName}:`, error)
          toast.error(`Failed to process ${fileName}`)
          setUploadingFiles(prev => prev.map(f =>
            f.path === filePath
              ? { ...f, status: 'error', error: 'Processing failed' }
              : f
          ))
        }
      }
    } catch (err) {
      if (String(err).includes('cancelled')) return
      console.error('File selection error:', err)
      toast.error('Unable to open file browser')
    }
  }

  const removeFile = (path: string) => {
    setUploadingFiles(prev => prev.filter(f => f.path !== path))
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Upload Zone */}
      <div className="relative rounded-lg border-2 border-dashed border-border hover:border-primary/50 transition-colors">
        <div className="p-8 text-center">
          <Upload className="mx-auto h-12 w-12 text-muted-fg mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            Upload Documents
          </h3>
          <p className="text-sm text-muted-fg mb-4">
            Select files to process and index for RAG
          </p>
          <button
            onClick={handleSelectFiles}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-fg rounded-md hover:bg-primary/90 transition-colors"
          >
            <FileText className="size-4" />
            Select Files
          </button>
          <p className="text-xs text-muted-fg mt-4">
            Supported: TXT, MD, DOC, DOCX
          </p>
        </div>
      </div>

      {/* Uploading Files List */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Processing Files</h4>
          {uploadingFiles.map((file) => (
            <div
              key={file.path}
              className="flex items-center gap-3 p-3 rounded-md border border-border bg-background"
            >
              {/* Status Icon */}
              <div className="flex-shrink-0">
                {file.status === 'uploading' && (
                  <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                )}
                {file.status === 'processing' && (
                  <div className="animate-pulse h-4 w-4 rounded-full bg-primary" />
                )}
                {file.status === 'complete' && (
                  <div className="h-4 w-4 rounded-full bg-green-500 flex items-center justify-center">
                    <span className="text-white text-xs">✓</span>
                  </div>
                )}
                {file.status === 'error' && (
                  <AlertCircle className="h-4 w-4 text-destructive" />
                )}
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-muted-fg">
                  {file.status === 'uploading' && 'Uploading...'}
                  {file.status === 'processing' && `Processing... ${file.progress || ''}`}
                  {file.status === 'complete' && `Complete • ${file.chunksCreated} chunks`}
                  {file.status === 'error' && `Error: ${file.error}`}
                </p>
              </div>

              {/* Remove Button */}
              {(file.status === 'complete' || file.status === 'error') && (
                <button
                  onClick={() => removeFile(file.path)}
                  className="p-1 hover:bg-accent rounded transition-colors"
                >
                  <X className="h-4 w-4 text-muted-fg" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

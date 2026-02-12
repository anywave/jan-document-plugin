/**
 * Document Upload Component
 * Allows users to select and upload documents for RAG processing
 */

import React, { useState, useRef } from 'react'
import { FileText, Upload, X, AlertCircle } from 'lucide-react'
import { processDocument, onProcessingProgress, type ProcessingProgress } from '../python-bridge'
import { toast } from 'sonner'

interface DocumentUploadProps {
  onUploadComplete?: (filePath: string, chunks: number) => void
  collectionName?: string
  className?: string
}

interface UploadingFile {
  path: string
  name: string
  size: number
  status: 'uploading' | 'processing' | 'complete' | 'error'
  step?: number
  totalSteps?: number
  stepName?: string
  stepDetail?: string
  percent?: number
  chunksCreated?: number
  processingTime?: number
  error?: string
  startedAt?: number
}

const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.doc', '.docx', '.rtf']

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatElapsed(startedAt: number): string {
  const elapsed = Math.floor((Date.now() - startedAt) / 1000)
  if (elapsed < 60) return `${elapsed}s`
  const min = Math.floor(elapsed / 60)
  const sec = elapsed % 60
  return `${min}m ${sec}s`
}

export function DocumentUpload({
  onUploadComplete,
  collectionName = 'documents',
  className = ''
}: DocumentUploadProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Timer to update elapsed display
  const [, setTick] = useState(0)
  React.useEffect(() => {
    const hasActive = uploadingFiles.some(
      f => f.status === 'uploading' || f.status === 'processing'
    )
    if (!hasActive) return

    const interval = setInterval(() => setTick(t => t + 1), 1000)
    return () => clearInterval(interval)
  }, [uploadingFiles])

  // Listen to processing progress events (granular step updates from Python)
  React.useEffect(() => {
    const setupListener = async () => {
      const unlisten = await onProcessingProgress((progress: ProcessingProgress) => {
        setUploadingFiles(prev => prev.map(file => {
          // Match by file path
          if (file.path === progress.file) {
            // Granular step progress from Python pipeline
            if (progress.progress && progress.step != null) {
              return {
                ...file,
                status: 'processing',
                step: progress.step,
                totalSteps: progress.total_steps,
                stepName: progress.step_name,
                stepDetail: progress.detail,
                percent: progress.percent,
              }
            }

            // Final status events from Rust
            if (progress.status === 'complete') {
              return {
                ...file,
                status: 'complete',
                chunksCreated: progress.chunks,
                percent: 100,
                stepName: 'Complete',
              }
            }
            if (progress.status === 'failed') {
              return {
                ...file,
                status: 'error',
                error: progress.error,
              }
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

  const handleFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files)

    // Validate file types
    const validFiles = fileArray.filter(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      return SUPPORTED_EXTENSIONS.includes(ext)
    })

    if (validFiles.length < fileArray.length) {
      toast.error(`Some files were skipped. Supported formats: ${SUPPORTED_EXTENSIONS.join(', ')}`)
    }

    if (validFiles.length === 0) return

    // Add files to uploading list with size and timestamp
    const newFiles: UploadingFile[] = validFiles.map(file => ({
      path: (file as any).path || file.name,
      name: file.name,
      size: file.size,
      status: 'uploading',
      startedAt: Date.now(),
    }))

    setUploadingFiles(prev => [...prev, ...newFiles])

    // Process each file
    for (const file of validFiles) {
      const filePath = (file as any).path || file.name

      try {
        const result = await processDocument(filePath, {
          collectionName,
          useOcr: true
        })

        if (result.success) {
          const timeStr = result.processing_time
            ? ` in ${result.processing_time}s`
            : ''
          toast.success(`Processed ${file.name}: ${result.chunks_created} chunks${timeStr}`)
          onUploadComplete?.(result.file_path, result.chunks_created)
        } else {
          toast.error(`Failed to process ${file.name}: ${result.error}`)
        }

        // Update file status
        setUploadingFiles(prev => prev.map(f =>
          f.path === filePath
            ? {
                ...f,
                status: result.success ? 'complete' : 'error',
                chunksCreated: result.chunks_created,
                processingTime: result.processing_time ?? undefined,
                percent: 100,
                error: result.error || undefined
              }
            : f
        ))
      } catch (error) {
        toast.error(`Error processing ${file.name}: ${String(error)}`)
        setUploadingFiles(prev => prev.map(f =>
          f.path === filePath
            ? { ...f, status: 'error', error: String(error) }
            : f
        ))
      }
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files)
    }
  }

  const removeFile = (path: string) => {
    setUploadingFiles(prev => prev.filter(f => f.path !== path))
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Drop Zone */}
      <div
        className={`
          relative rounded-lg border-2 border-dashed transition-colors
          ${dragActive
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50'
          }
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={SUPPORTED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="p-8 text-center">
          <Upload className="mx-auto h-12 w-12 text-muted-fg mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            Upload Documents
          </h3>
          <p className="text-sm text-muted-fg mb-4">
            Drag and drop files here, or click to select
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-fg rounded-md hover:bg-primary/90 transition-colors"
          >
            <FileText className="size-4" />
            Select Files
          </button>
          <p className="text-xs text-muted-fg mt-4">
            Supported: TXT, MD, DOC, DOCX, RTF (no PDFs)
          </p>
        </div>
      </div>

      {/* Uploading Files List */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Processing Files</h4>
          {uploadingFiles.map((file) => (
            <div
              key={file.path}
              className="p-3 rounded-md border border-border bg-background space-y-2"
            >
              {/* Header row: icon, name, size, elapsed, remove */}
              <div className="flex items-center gap-3">
                {/* Status Icon */}
                <div className="flex-shrink-0">
                  {(file.status === 'uploading' || file.status === 'processing') && (
                    <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
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

                {/* File name and size */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-muted-fg">
                    {formatFileSize(file.size)}
                    {file.startedAt && (file.status === 'uploading' || file.status === 'processing') && (
                      <> — {formatElapsed(file.startedAt)} elapsed</>
                    )}
                    {file.status === 'complete' && file.processingTime && (
                      <> — completed in {file.processingTime}s</>
                    )}
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

              {/* Progress bar */}
              {(file.status === 'uploading' || file.status === 'processing') && (
                <div className="space-y-1">
                  <div className="w-full h-2 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${file.percent || (file.status === 'uploading' ? 5 : 10)}%` }}
                    />
                  </div>
                  {/* Step indicator */}
                  <div className="flex items-center justify-between text-xs text-muted-fg">
                    <span>
                      {file.stepName
                        ? `Step ${file.step}/${file.totalSteps}: ${file.stepName}`
                        : 'Starting pipeline...'
                      }
                    </span>
                    <span>{file.percent || 0}%</span>
                  </div>
                  {file.stepDetail && (
                    <p className="text-xs text-muted-fg/80 truncate">
                      {file.stepDetail}
                    </p>
                  )}
                </div>
              )}

              {/* Complete summary */}
              {file.status === 'complete' && (
                <p className="text-xs text-green-600">
                  {file.chunksCreated} chunks created and indexed
                </p>
              )}

              {/* Error message */}
              {file.status === 'error' && (
                <p className="text-xs text-destructive">
                  {file.error}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

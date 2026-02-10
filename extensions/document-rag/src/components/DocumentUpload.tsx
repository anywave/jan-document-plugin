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
  status: 'uploading' | 'processing' | 'complete' | 'error'
  progress?: string
  chunksCreated?: number
  error?: string
}

const SUPPORTED_EXTENSIONS = [
  '.pdf', '.docx', '.doc', '.txt', '.md',
  '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'
]

export function DocumentUpload({
  onUploadComplete,
  collectionName = 'documents',
  className = ''
}: DocumentUploadProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

    // Add files to uploading list
    const newFiles: UploadingFile[] = validFiles.map(file => ({
      path: (file as any).path || file.name, // Electron provides .path
      name: file.name,
      status: 'uploading'
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
          toast.success(`Processed ${file.name}: ${result.chunks_created} chunks`)
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
            Supported: PDF, DOCX, TXT, MD, Images
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

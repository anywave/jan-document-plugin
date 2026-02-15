'use client'

import TextareaAutosize from 'react-textarea-autosize'
import { cn, toGigabytes } from '@/lib/utils'
import { useNavigate } from '@tanstack/react-router'
import { route } from '@/constants/routes'
import { usePrompt } from '@/hooks/usePrompt'
import { useThreads } from '@/hooks/useThreads'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { ArrowRight } from 'lucide-react'
import {
  IconPaperclip,
  IconWorld,
  IconAtom,
  IconEye,
  IconTool,
  IconCodeCircle2,
  IconPlayerStopFilled,
  IconX,
  IconFileSearch,
  IconSparkles,
  IconFolder,
  IconDatabase,
  IconDeviceMobile,
} from '@tabler/icons-react'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { useGeneralSetting } from '@/hooks/useGeneralSetting'
import { useModelProvider } from '@/hooks/useModelProvider'
import { localStorageKey } from '@/constants/localStorage'

import { useAppState } from '@/hooks/useAppState'
import { MovingBorder } from './MovingBorder'
import { useChat } from '@/hooks/useChat'
import DropdownModelProvider from '@/containers/DropdownModelProvider'
import { ModelLoader } from '@/containers/loaders/ModelLoader'
import DropdownToolsAvailable from '@/containers/DropdownToolsAvailable'
import { getConnectedServers } from '@/services/mcp'
import { ContextIndicator } from '@/extensions/document-rag/src/components/ContextIndicator'
import { DocumentSearchModal } from '@/extensions/document-rag/src/components/DocumentSearchModal'
import {
  processDocument,
  queryDocuments,
  processDocumentBatch,
  scanDirectory,
  onBatchFileResult,
  onProcessingProgress,
  type BatchFileResult,
} from '@/extensions/document-rag/src/python-bridge'
import { useDocumentContext } from '@/extensions/document-rag/src/hooks/useDocumentContext'
import { open } from '@tauri-apps/plugin-dialog'
import { getCurrentWebviewWindow } from '@tauri-apps/api/webviewWindow'
import { toast } from 'sonner'
import { VoiceRecorder } from '@/components/VoiceRecorder'
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'
import { useVoiceRelay } from '@/hooks/useVoiceRelay'
import {
  startVoiceRelay,
  stopVoiceRelay,
  getVoiceRelayStatus,
} from '@/extensions/document-rag/src/python-bridge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { CoherenceBar } from '@/components/CoherenceBar'

type ChatInputProps = {
  className?: string
  showSpeedToken?: boolean
  model?: ThreadModel
  initialMessage?: boolean
}

const ChatInput = ({ model, className, initialMessage }: ChatInputProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [isFocused, setIsFocused] = useState(false)
  const [rows, setRows] = useState(1)
  const { streamingContent, abortControllers, loadingModel, tools } =
    useAppState()
  const { prompt, setPrompt } = usePrompt()
  const { currentThreadId } = useThreads()
  const { t } = useTranslation()
  const { spellCheckChatInput, experimentalFeatures } = useGeneralSetting()

  const maxRows = 10

  const { selectedModel } = useModelProvider()
  const { sendMessage } = useChat()
  const navigate = useNavigate()

  const openDocs = (section: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    navigate({ to: `${route.docs}#${section}` as any })
  }
  const [message, setMessage] = useState('')
  const [dropdownToolsAvailable, setDropdownToolsAvailable] = useState(false)
  const [tooltipToolsAvailable, setTooltipToolsAvailable] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<
    Array<{
      name: string
      type: string
      size: number
      base64: string
      dataUrl: string
    }>
  >([])
  const [connectedServers, setConnectedServers] = useState<string[]>([])
  const [showDocSearch, setShowDocSearch] = useState(false)
  const [smartProcessing, setSmartProcessing] = useState(false)
  const [ragEnabled, setRagEnabled] = useState(() => {
    try {
      return localStorage.getItem(localStorageKey.ragEnabled) === 'true'
    } catch {
      return false
    }
  })

  const toggleRag = () => {
    setRagEnabled((prev) => {
      const next = !prev
      try { localStorage.setItem(localStorageKey.ragEnabled, String(next)) } catch { /* quota */ }
      return next
    })
  }
  const [isBatchProcessing, setIsBatchProcessing] = useState(false)
  const [batchFiles, setBatchFiles] = useState<
    Array<{
      path: string
      name: string
      status: 'pending' | 'processing' | 'complete' | 'error'
      chunks?: number
      error?: string
    }>
  >([])

  // Allowed extensions for document processing
  const ALLOWED_DOC_EXTENSIONS = ['txt', 'md', 'doc', 'docx', 'rtf']

  // Refs to read current state inside event listeners without re-registering
  const isBatchProcessingRef = useRef(isBatchProcessing)
  isBatchProcessingRef.current = isBatchProcessing
  const handleBatchProcessRef = useRef<(paths: string[]) => void>(() => {})

  // Speech recognition
  const {
    transcript,
    isListening,
    isSupported: isSpeechSupported,
    toggleListening,
    resetTranscript,
    error: speechError,
  } = useSpeechRecognition()

  // Voice relay (phone-as-mic over Wi-Fi)
  const {
    transcript: relayTranscript,
    isConnected: isRelayConnected,
    setupUrl: relaySetupUrl,
    connect: connectRelay,
    disconnect: disconnectRelay,
    resetTranscript: resetRelayTranscript,
    error: relayError,
  } = useVoiceRelay()
  const [relayActive, setRelayActive] = useState(false)
  const [showQrModal, setShowQrModal] = useState(false)

  // Show QR modal when voice relay starts and setup URL is ready
  useEffect(() => {
    if (relaySetupUrl && relayActive) {
      setShowQrModal(true)
    } else {
      setShowQrModal(false)
    }
  }, [relaySetupUrl, relayActive])

  // Sync local speech transcript to prompt
  useEffect(() => {
    if (transcript) {
      setPrompt((prev) => {
        const combined = prev ? `${prev} ${transcript}` : transcript
        return combined
      })
      resetTranscript()
    }
  }, [transcript, resetTranscript])

  // Sync relay transcript to prompt (same pipeline as local speech)
  useEffect(() => {
    if (relayTranscript) {
      setPrompt((prev) => {
        const combined = prev ? `${prev} ${relayTranscript}` : relayTranscript
        return combined
      })
      resetRelayTranscript()
    }
  }, [relayTranscript, resetRelayTranscript])

  // Toggle voice relay: start server + connect WebSocket
  const toggleVoiceRelay = useCallback(async () => {
    if (relayActive) {
      disconnectRelay()
      await stopVoiceRelay().catch(() => {})
      setRelayActive(false)
    } else {
      try {
        const status = await startVoiceRelay()
        if (status.running) {
          connectRelay()
          setRelayActive(true)
        }
      } catch (err) {
        console.error('Failed to start voice relay:', err)
      }
    }
  }, [relayActive, connectRelay, disconnectRelay])

  // Keyboard shortcut for voice (Ctrl+M)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'm') {
        e.preventDefault()
        toggleListening()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [toggleListening])

  // Check for connected MCP servers (only in Tauri context)
  useEffect(() => {
    if (!(window as any).__TAURI_INTERNALS__) return

    const checkConnectedServers = async () => {
      try {
        const servers = await getConnectedServers()
        setConnectedServers(servers)
      } catch (error) {
        console.error('Failed to get connected servers:', error)
        setConnectedServers([])
      }
    }

    checkConnectedServers()

    // Poll for connected servers every 3 seconds
    const intervalId = setInterval(checkConnectedServers, 3000)

    return () => clearInterval(intervalId)
  }, [])

  // Drag-and-drop document files onto chat (registered once, reads refs)
  useEffect(() => {
    // Only register in Tauri context (not plain browser)
    if (!(window as any).__TAURI_INTERNALS__) return
    let cancelled = false
    let unlisten: (() => void) | undefined
    try {
      getCurrentWebviewWindow()
        .onDragDropEvent((event) => {
          if (event.payload.type === 'drop' && !isBatchProcessingRef.current) {
            const exts = ALLOWED_DOC_EXTENSIONS
            const paths = event.payload.paths.filter((p: string) => {
              const ext = p.split('.').pop()?.toLowerCase() || ''
              return exts.includes(ext)
            })
            if (paths.length > 0) {
              handleBatchProcessRef.current(paths)
            } else if (event.payload.paths.length > 0) {
              toast.error(`No supported document files. Allowed: ${exts.join(', ')}`)
            }
          }
        })
        .then((fn) => {
          if (cancelled) { fn() } else { unlisten = fn }
        })
        .catch((err) => console.error('Failed to register drag-drop listener:', err))
    } catch (err) {
      console.warn('Drag-drop not available (not in Tauri context):', err)
    }
    return () => {
      cancelled = true
      unlisten?.()
    }
  }, [])

  // Listen for per-file batch results to update pill strip in real-time
  useEffect(() => {
    if (!(window as any).__TAURI_INTERNALS__) return
    let cancelled = false
    let unlisten: (() => void) | undefined
    onBatchFileResult((result: BatchFileResult) => {
      setBatchFiles((prev) =>
        prev.map((f) =>
          f.path === result.file_path
            ? {
                ...f,
                status: result.success ? 'complete' : 'error',
                chunks: result.chunks_created,
                error: result.error ?? undefined,
              }
            : f
        )
      )
    })
      .then((fn) => {
        if (cancelled) { fn() } else { unlisten = fn }
      })
      .catch((err) => console.error('Failed to register batch result listener:', err))
    return () => {
      cancelled = true
      unlisten?.()
    }
  }, [])

  // Listen for progress events to mark files as "processing"
  useEffect(() => {
    if (!(window as any).__TAURI_INTERNALS__) return
    let cancelled = false
    let unlisten: (() => void) | undefined
    onProcessingProgress((progress) => {
      if (progress.batch_index !== undefined && progress.file) {
        setBatchFiles((prev) =>
          prev.map((f) =>
            f.path === progress.file && f.status === 'pending'
              ? { ...f, status: 'processing' }
              : f
          )
        )
      }
    })
      .then((fn) => {
        if (cancelled) { fn() } else { unlisten = fn }
      })
      .catch((err) => console.error('Failed to register progress listener:', err))
    return () => {
      cancelled = true
      unlisten?.()
    }
  }, [])

  // Check if there are active MCP servers
  const hasActiveMCPServers = connectedServers.length > 0 || tools.length > 0

  const handleSendMesage = (prompt: string) => {
    if (!selectedModel) {
      setMessage('Please select a model to start chatting.')
      return
    }
    if (!prompt.trim()) {
      return
    }
    setMessage('')
    sendMessage(prompt, true, ragEnabled)
  }

  useEffect(() => {
    const handleFocusIn = () => {
      if (document.activeElement === textareaRef.current) {
        setIsFocused(true)
      }
    }

    const handleFocusOut = () => {
      if (document.activeElement !== textareaRef.current) {
        setIsFocused(false)
      }
    }

    document.addEventListener('focusin', handleFocusIn)
    document.addEventListener('focusout', handleFocusOut)

    return () => {
      document.removeEventListener('focusin', handleFocusIn)
      document.removeEventListener('focusout', handleFocusOut)
    }
  }, [])

  // Focus when component mounts
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [])

  useEffect(() => {
    if (tooltipToolsAvailable && dropdownToolsAvailable) {
      setTooltipToolsAvailable(false)
    }
  }, [dropdownToolsAvailable, tooltipToolsAvailable])

  // Focus when thread changes
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [currentThreadId])

  // Focus when streaming content finishes
  useEffect(() => {
    if (!streamingContent && textareaRef.current) {
      // Small delay to ensure UI has updated
      setTimeout(() => {
        textareaRef.current?.focus()
      }, 10)
    }
  }, [streamingContent])

  const stopStreaming = useCallback(
    (threadId: string) => {
      abortControllers[threadId]?.abort()
    },
    [abortControllers]
  )

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleAttachmentClick = () => {
    fileInputRef.current?.click()
  }

  const handleRemoveFile = (indexToRemove: number) => {
    setUploadedFiles((prev) =>
      prev.filter((_, index) => index !== indexToRemove)
    )
  }

  const getFileTypeFromExtension = (fileName: string): string => {
    const extension = fileName.toLowerCase().split('.').pop()
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg'
      case 'png':
        return 'image/png'
      case 'pdf':
        return 'application/pdf'
      default:
        return ''
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files

    if (files && files.length > 0) {
      const maxSize = 10 * 1024 * 1024 // 10MB in bytes
      const newFiles: Array<{
        name: string
        type: string
        size: number
        base64: string
        dataUrl: string
      }> = []

      Array.from(files).forEach((file) => {
        // Check file size
        if (file.size > maxSize) {
          setMessage(`File is too large. Maximum size is 10MB.`)
          // Reset file input to allow re-uploading
          if (fileInputRef.current) {
            fileInputRef.current.value = ''
          }
          return
        }

        // Get file type - use extension as fallback if MIME type is incorrect
        const detectedType = file.type || getFileTypeFromExtension(file.name)
        const actualType = getFileTypeFromExtension(file.name) || detectedType

        // Check file type
        const allowedTypes = [
          'image/jpg',
          'image/jpeg',
          'image/png',
          'application/pdf',
        ]

        if (!allowedTypes.includes(actualType)) {
          setMessage(
            `File is not supported. Only JPEG, JPG, PNG, and PDF files are allowed.`
          )
          // Reset file input to allow re-uploading
          if (fileInputRef.current) {
            fileInputRef.current.value = ''
          }
          return
        }

        const reader = new FileReader()
        reader.onload = () => {
          const result = reader.result
          if (typeof result === 'string') {
            const base64String = result.split(',')[1]
            const fileData = {
              name: file.name,
              size: file.size,
              type: actualType,
              base64: base64String,
              dataUrl: result,
            }
            newFiles.push(fileData)
            // Update state
            if (
              newFiles.length ===
              Array.from(files).filter((f) => {
                const fType = getFileTypeFromExtension(f.name) || f.type
                return f.size <= maxSize && allowedTypes.includes(fType)
              }).length
            ) {
              setUploadedFiles((prev) => {
                const updated = [...prev, ...newFiles]
                return updated
              })
              // Reset the file input value to allow re-uploading the same file
              if (fileInputRef.current) {
                fileInputRef.current.value = ''
                setMessage('')
              }
            }
          }
        }
        reader.readAsDataURL(file)
      })
    }

    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }

  // Batch process multiple files — model loaded once, per-file progress
  const handleBatchProcess = async (filePaths: string[]) => {
    if (isBatchProcessing) {
      toast.error('Batch processing already in progress')
      return
    }
    if (filePaths.length === 0) return

    // Single file → use existing detailed path
    if (filePaths.length === 1) {
      const filePath = filePaths[0]
      const fileName = filePath.split(/[\\/]/).pop() || filePath
      toast.loading(`Processing "${fileName}"...`, { id: `doc-${fileName}`, duration: Infinity })

      processDocument(filePath, { collectionName: 'documents', smart: smartProcessing })
        .then((result) => {
          if (result.success) {
            const summary = result.document_summary
            const time = result.processing_time ? ` in ${result.processing_time}s` : ''
            toast.success(
              `"${fileName}" indexed — ${result.chunks_created} chunks, ` +
              `${summary?.word_count?.toLocaleString() || '?'} words${time}`,
              { id: `doc-${fileName}` }
            )
            const sections = summary?.sections_detected?.length
              ? `\nDetected sections: ${summary.sections_detected.join(', ')}`
              : ''
            const stats = summary
              ? `${summary.word_count.toLocaleString()} words, ${summary.chunks_created} chunks, ${summary.file_size_mb} MB`
              : `${result.chunks_created} chunks`
            sendMessage(
              `I just uploaded "${fileName}" (${stats}).${sections}\n\n` +
              `Please provide a structured summary of this document including: ` +
              `key topics, main arguments or findings, and important details.`
            )
          } else {
            toast.error(`Failed: ${result.error || 'Unknown error'}`, { id: `doc-${fileName}` })
          }
        })
        .catch((err) => {
          console.error('Document processing error:', err)
          toast.error('Failed to process document', { id: `doc-${fileName}` })
        })
      return
    }

    // Multi-file → batch path
    setIsBatchProcessing(true)
    const initialBatch = filePaths.map((p) => ({
      path: p,
      name: p.split(/[\\/]/).pop() || p,
      status: 'pending' as const,
    }))
    setBatchFiles(initialBatch)
    toast.loading(`Batch processing ${filePaths.length} files...`, { id: 'batch', duration: Infinity })

    try {
      const result = await processDocumentBatch(filePaths, {
        collectionName: 'documents',
        smart: smartProcessing,
      })

      toast.success(
        `Batch complete: ${result.success_count}/${result.total_files} succeeded in ${result.total_time}s`,
        { id: 'batch' }
      )

      // Brief multi-file acknowledgment
      const fileNames = filePaths.map((p) => p.split(/[\\/]/).pop()).join(', ')
      sendMessage(
        `I just indexed ${result.success_count} document${result.success_count !== 1 ? 's' : ''}: ${fileNames}. ` +
        `Total: ${result.results.reduce((sum, r) => sum + r.chunks_created, 0)} chunks in ${result.total_time}s.` +
        (result.error_count > 0
          ? ` ${result.error_count} file${result.error_count !== 1 ? 's' : ''} failed.`
          : '') +
        `\n\nPlease briefly acknowledge the indexed documents.`
      )
    } catch (err) {
      console.error('Batch processing error:', err)
      toast.error('Batch processing failed', { id: 'batch' })
    } finally {
      setIsBatchProcessing(false)
      // Clear batch files after a short delay to let user see final state
      setTimeout(() => setBatchFiles([]), 3000)
    }
  }
  handleBatchProcessRef.current = handleBatchProcess

  const handleDocUpload = async () => {
    if (isBatchProcessing) return
    try {
      const selected = await open({
        multiple: true,
        filters: [{ name: 'Documents', extensions: ALLOWED_DOC_EXTENSIONS }],
      })
      if (!selected) return

      // open() with multiple:true returns string | string[]
      const paths = Array.isArray(selected) ? selected : [selected]
      handleBatchProcess(paths)
    } catch (err) {
      if (String(err).includes('cancelled')) return
      console.error('File selection error:', err)
      toast.error('Unable to open file browser')
    }
  }

  const handleFolderUpload = async () => {
    if (isBatchProcessing) return
    try {
      const selected = await open({ directory: true })
      if (!selected) return
      const dirPath = typeof selected === 'string' ? selected : selected

      toast.loading('Scanning folder...', { id: 'folder-scan' })
      const scanResult = await scanDirectory(dirPath)

      if (scanResult.files.length === 0) {
        toast.error(`No supported files found (skipped ${scanResult.skipped})`, { id: 'folder-scan' })
        return
      }

      const sizeMB = (scanResult.total_size / (1024 * 1024)).toFixed(1)
      toast.success(
        `Found ${scanResult.files.length} files (${sizeMB} MB), ${scanResult.skipped} skipped`,
        { id: 'folder-scan' }
      )

      handleBatchProcess(scanResult.files.map((f) => f.path))
    } catch (err) {
      if (String(err).includes('cancelled')) return
      console.error('Folder scan error:', err)
      toast.error('Unable to scan folder', { id: 'folder-scan' })
    }
  }

  return (
    <div className="relative">
      <div className="relative">
        <div
          className={cn(
            'relative overflow-hidden p-[2px] rounded-lg',
            Boolean(streamingContent) && 'opacity-70'
          )}
        >
          {streamingContent && (
            <div className="absolute inset-0">
              <MovingBorder rx="10%" ry="10%">
                <div
                  className={cn(
                    'h-100 w-100 bg-[radial-gradient(var(--app-primary),transparent_60%)]'
                  )}
                />
              </MovingBorder>
            </div>
          )}

          <div
            className={cn(
              'relative z-20 px-0 pb-10 border border-main-view-fg/5 rounded-lg text-main-view-fg bg-main-view',
              isFocused && 'ring-1 ring-main-view-fg/10'
            )}
          >
            {/* Document Context Indicator */}
            {currentThreadId && (
              <div className="px-4 pt-3">
                <ContextIndicator threadId={currentThreadId} />
              </div>
            )}
            {uploadedFiles.length > 0 && (
              <div className="flex gap-3 items-center p-2 pb-0">
                {uploadedFiles.map((file, index) => {
                  return (
                    <div
                      key={index}
                      className={cn(
                        'relative border border-main-view-fg/5 rounded-lg',
                        file.type.startsWith('image/') ? 'size-14' : 'h-14 '
                      )}
                    >
                      {file.type.startsWith('image/') && (
                        <img
                          className="object-cover w-full h-full rounded-lg"
                          src={file.dataUrl}
                          alt={`${file.name} - ${index}`}
                        />
                      )}
                      {file.type === 'application/pdf' && (
                        <div className="bg-main-view-fg/4 h-full rounded-lg p-2 max-w-[400px] pr-4">
                          <div className="flex gap-2 items-center justify-center h-full">
                            <div className="size-10 rounded-md bg-main-view shrink-0 flex items-center justify-center">
                              <span className="uppercase font-bold">
                                {file.name.split('.').pop()}
                              </span>
                            </div>
                            <div className="truncate">
                              <h6 className="truncate mb-0.5 text-main-view-fg/80">
                                {file.name}
                              </h6>
                              <p className="text-xs text-main-view-fg/70">
                                {toGigabytes(file.size)}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                      <div
                        className="absolute -top-1 -right-2.5 bg-destructive size-5 flex rounded-full items-center justify-center cursor-pointer"
                        onClick={() => handleRemoveFile(index)}
                      >
                        <IconX className="text-destructive-fg" size={16} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
            {/* Batch Progress Pill Strip */}
            {batchFiles.length > 0 && (
              <div className="px-4 pt-2 flex flex-wrap gap-1.5">
                {batchFiles.map((f, i) => (
                  <div
                    key={i}
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
                      f.status === 'pending' && 'bg-main-view-fg/5 border-main-view-fg/10 text-main-view-fg/50',
                      f.status === 'processing' && 'bg-blue-500/10 border-blue-500/30 text-blue-500',
                      f.status === 'complete' && 'bg-green-500/10 border-green-500/30 text-green-600',
                      f.status === 'error' && 'bg-red-500/10 border-red-500/30 text-red-500'
                    )}
                    title={f.error || (f.chunks !== undefined ? `${f.chunks} chunks` : f.status)}
                  >
                    {f.status === 'processing' && (
                      <span className="animate-spin h-3 w-3 border border-current border-t-transparent rounded-full" />
                    )}
                    <span className="truncate max-w-[120px]">{f.name}</span>
                    {f.status === 'complete' && f.chunks !== undefined && (
                      <span className="text-[10px] opacity-70">{f.chunks}</span>
                    )}
                  </div>
                ))}
                {isBatchProcessing && (
                  <div className="text-xs text-main-view-fg/40 self-center ml-1">
                    {batchFiles.filter((f) => f.status === 'complete').length}/{batchFiles.length}
                  </div>
                )}
              </div>
            )}
            <TextareaAutosize
              ref={textareaRef}
              disabled={Boolean(streamingContent) || isBatchProcessing}
              minRows={2}
              rows={1}
              maxRows={10}
              value={prompt}
              data-test-id={'chat-input'}
              onChange={(e) => {
                setPrompt(e.target.value)
                // Count the number of newlines to estimate rows
                const newRows = (e.target.value.match(/\n/g) || []).length + 1
                setRows(Math.min(newRows, maxRows))
              }}
              onKeyDown={(e) => {
                // e.keyCode 229 is for IME input with Safari
                const isComposing = e.nativeEvent.isComposing || e.keyCode === 229;
                if (e.key === 'Enter' && !e.shiftKey && prompt.trim() && !isComposing) {
                  e.preventDefault()
                  // Submit the message when Enter is pressed without Shift
                  handleSendMesage(prompt)
                  // When Shift+Enter is pressed, a new line is added (default behavior)
                }
              }}
              placeholder={t('common:placeholder.chatInput')}
              autoFocus
              spellCheck={spellCheckChatInput}
              data-gramm={spellCheckChatInput}
              data-gramm_editor={spellCheckChatInput}
              data-gramm_grammarly={spellCheckChatInput}
              className={cn(
                'bg-transparent pt-4 w-full flex-shrink-0 border-none resize-none outline-0 px-4',
                rows < maxRows && 'scrollbar-hide',
                className
              )}
            />
          </div>
        </div>

        <div className="absolute z-20 bg-transparent bottom-0 w-full p-2 ">
          <div className="flex justify-between items-center w-full">
            <div className="px-1 flex flex-col gap-0.5">
              <div
                className={cn(
                  'px-1 flex items-center gap-1 flex-wrap',
                  streamingContent && 'opacity-50 pointer-events-none'
                )}
              >
                {model?.provider === 'llamacpp' && loadingModel ? (
                  <ModelLoader />
                ) : (
                  <DropdownModelProvider
                    model={model}
                    useLastUsedModel={initialMessage}
                  />
                )}
                {/* File attachment - always available */}
                <div
                  className="h-6 hidden p-1 items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1"
                  onClick={handleAttachmentClick}
                >
                  <IconPaperclip size={18} className="text-main-view-fg/50" />
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </div>
                {/* Microphone - always available - Temp Hide */}
                {/* <div className="h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1">
                <IconMicrophone size={18} className="text-main-view-fg/50" />
              </div> */}
                {selectedModel?.capabilities?.includes('vision') && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger disabled={dropdownToolsAvailable}>
                        <div
                          className="h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1"
                          onContextMenu={openDocs('vision')}
                        >
                          <IconEye size={18} className="text-main-view-fg/50" />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{t('vision')}</p>

                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                {selectedModel?.capabilities?.includes('embeddings') && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div
                          className="h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1"
                          onContextMenu={openDocs('embeddings')}
                        >
                          <IconCodeCircle2
                            size={18}
                            className="text-main-view-fg/50"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{t('embeddings')}</p>

                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}

                {experimentalFeatures &&
                  selectedModel?.capabilities?.includes('tools') &&
                  hasActiveMCPServers && (
                    <TooltipProvider>
                      <Tooltip
                        open={tooltipToolsAvailable}
                        onOpenChange={setTooltipToolsAvailable}
                      >
                        <TooltipTrigger
                          asChild
                          disabled={dropdownToolsAvailable}
                        >
                          <div
                            onClick={(e) => {
                              setDropdownToolsAvailable(false)
                              e.stopPropagation()
                            }}
                            onContextMenu={openDocs('tools')}
                          >
                            <DropdownToolsAvailable
                              initialMessage={initialMessage}
                              onOpenChange={(isOpen) => {
                                setDropdownToolsAvailable(isOpen)
                                setTooltipToolsAvailable(false)
                              }}
                            >
                              {(isOpen, toolsCount) => {
                                return (
                                  <div
                                    className={cn(
                                      'h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1 cursor-pointer relative',
                                      isOpen && 'bg-main-view-fg/10'
                                    )}
                                  >
                                    <IconTool
                                      size={18}
                                      className="text-main-view-fg/50"
                                    />
                                    {toolsCount > 0 && (
                                      <div className="absolute -top-2 -right-2 bg-accent text-accent-fg text-xs rounded-full size-5 flex items-center justify-center font-medium">
                                        <span className="leading-0 text-xs">
                                          {toolsCount > 99 ? '99+' : toolsCount}
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                )
                              }}
                            </DropdownToolsAvailable>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{t('tools')}</p>
  
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                {selectedModel?.capabilities?.includes('web_search') && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div
                          className="h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1"
                          onContextMenu={openDocs('web-search')}
                        >
                          <IconWorld
                            size={18}
                            className="text-main-view-fg/50"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Web Search</p>

                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                {selectedModel?.capabilities?.includes('reasoning') && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div
                          className="h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1"
                          onContextMenu={openDocs('reasoning')}
                        >
                          <IconAtom
                            size={18}
                            className="text-main-view-fg/50"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{t('reasoning')}</p>

                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                {/* Document Upload - Always available, supports multi-select */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        onClick={handleDocUpload}
                        onContextMenu={openDocs('upload-documents')}
                        className={cn(
                          "h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1 cursor-pointer",
                          isBatchProcessing && "opacity-50 pointer-events-none"
                        )}
                      >
                        <IconPaperclip
                          size={18}
                          className="text-main-view-fg/50"
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Upload Documents</p>

                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {/* Upload Folder */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        onClick={handleFolderUpload}
                        onContextMenu={openDocs('upload-folder')}
                        className={cn(
                          "h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1 cursor-pointer",
                          isBatchProcessing && "opacity-50 pointer-events-none"
                        )}
                      >
                        <IconFolder
                          size={18}
                          className="text-main-view-fg/50"
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Upload Folder</p>

                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {/* Document RAG Toggle */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        onClick={toggleRag}
                        onContextMenu={openDocs('rag-toggle')}
                        className={cn(
                          "h-6 p-1 flex items-center justify-center rounded-sm transition-all duration-200 ease-in-out gap-1 cursor-pointer",
                          ragEnabled
                            ? "bg-primary/20 text-primary"
                            : "hover:bg-main-view-fg/10 text-main-view-fg/50"
                        )}
                      >
                        <IconDatabase size={18} />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="font-semibold">{ragEnabled ? 'Document RAG: ON' : 'Document RAG: OFF'}</p>
                      <p className="text-xs mt-1">
                        {ragEnabled
                          ? 'Chat messages will search your indexed documents and include relevant context. May add latency.'
                          : 'Chat goes directly to the model without document retrieval. Toggle ON to use your indexed documents.'}
                      </p>

                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {/* Smart Processing Toggle */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        onClick={() => setSmartProcessing(!smartProcessing)}
                        onContextMenu={openDocs('smart-processing')}
                        className={cn(
                          "h-6 p-1 flex items-center justify-center rounded-sm transition-all duration-200 ease-in-out gap-1 cursor-pointer",
                          smartProcessing
                            ? "bg-primary/20 text-primary"
                            : "hover:bg-main-view-fg/10 text-main-view-fg/50"
                        )}
                      >
                        <IconSparkles size={18} />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="font-semibold">{smartProcessing ? 'Smart Processing: ON' : 'Smart Processing: OFF'}</p>
                      <p className="text-xs mt-1">
                        {smartProcessing
                          ? 'Structure-aware chunking — preserves sections, headings, and paragraphs. Better for legal docs, reports, and research papers. Fewer but larger, more meaningful chunks.'
                          : 'Standard chunking — fast, fixed-size 500 char splits. Good for quick lookups and short documents.'}
                      </p>

                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {/* Search Indexed Documents */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        onClick={() => setShowDocSearch(true)}
                        onContextMenu={openDocs('search-documents')}
                        className="h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1 cursor-pointer"
                      >
                        <IconFileSearch
                          size={18}
                          className="text-main-view-fg/50"
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Search Documents</p>

                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {/* Voice Input - Always available */}
                <VoiceRecorder
                  isRecording={isListening}
                  isSupported={isSpeechSupported}
                  onToggle={toggleListening}
                  error={speechError}
                  onContextMenu={openDocs('voice-input')}
                />
                {/* Phone Mic (Voice Relay) */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        onClick={toggleVoiceRelay}
                        onContextMenu={openDocs('voice-relay')}
                        className={cn(
                          'h-6 p-1 flex items-center justify-center rounded-sm transition-all duration-200 ease-in-out gap-1 cursor-pointer relative',
                          relayActive && isRelayConnected
                            ? 'bg-green-500/20'
                            : relayActive
                              ? 'bg-yellow-500/20'
                              : 'hover:bg-main-view-fg/10'
                        )}
                      >
                        {relayActive && isRelayConnected && (
                          <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-green-500" />
                        )}
                        <IconDeviceMobile
                          size={18}
                          className={cn(
                            relayActive && isRelayConnected
                              ? 'text-green-500'
                              : relayActive
                                ? 'text-yellow-500'
                                : 'text-main-view-fg/50'
                          )}
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="font-semibold">
                        {relayActive
                          ? isRelayConnected
                            ? 'Phone Mic: Connected'
                            : 'Phone Mic: Starting...'
                          : 'Phone Mic (Wi-Fi)'}
                      </p>
                      <p className="text-xs mt-1">
                        {relayActive && relaySetupUrl
                          ? `Open ${relaySetupUrl} on your phone or scan the QR code to use your phone as a wireless microphone.`
                          : relayError
                            ? relayError
                            : 'Use your phone as a wireless microphone via Wi-Fi. Your phone\'s native speech-to-text transcribes voice, then sends the text to MOBIUS.'}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <span className="text-[10px] text-main-view-fg/30 italic select-none ml-[140px]">Right click for more info...</span>
            </div>

            {streamingContent ? (
              <Button
                variant="destructive"
                size="icon"
                onClick={() =>
                  stopStreaming(currentThreadId ?? streamingContent.thread_id)
                }
              >
                <IconPlayerStopFilled />
              </Button>
            ) : (
              <Button
                variant={!prompt.trim() ? null : 'default'}
                size="icon"
                disabled={!prompt.trim()}
                data-test-id="send-message-button"
                onClick={() => handleSendMesage(prompt)}
              >
                {streamingContent ? (
                  <span className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                ) : (
                  <ArrowRight className="text-primary-fg" />
                )}
              </Button>
            )}
          </div>
        </div>
        <CoherenceBar />
      </div>
      {message && (
        <div className="bg-main-view-fg/2 -mt-0.5 mx-2 pb-2 px-3 pt-1.5 rounded-b-lg text-xs text-destructive transition-all duration-200 ease-in-out">
          <div className="flex items-center gap-1 justify-between">
            {message}
            <IconX
              className="size-3 text-main-view-fg/30 cursor-pointer"
              onClick={() => {
                setMessage('')
                // Reset file input to allow re-uploading the same file
                if (fileInputRef.current) {
                  fileInputRef.current.value = ''
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Document Search Modal */}
      {currentThreadId && (
        <DocumentSearchModal
          isOpen={showDocSearch}
          onClose={() => setShowDocSearch(false)}
          threadId={currentThreadId}
        />
      )}

      {/* Voice Relay QR Code Modal */}
      <Dialog open={showQrModal} onOpenChange={setShowQrModal}>
        <DialogContent className="sm:max-w-md" aria-describedby="qr-desc">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <IconDeviceMobile size={22} />
              Phone Mic Setup
            </DialogTitle>
            <DialogDescription id="qr-desc">
              Scan this QR code with your phone to use it as a wireless microphone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center gap-4 py-4">
            {relaySetupUrl ? (
              <img
                src={`http://localhost:${new URL(relaySetupUrl).port || '8089'}/qr.svg`}
                alt="QR Code for phone mic setup"
                className="bg-white rounded-xl p-4"
                style={{ width: 300, height: 300 }}
              />
            ) : (
              <div className="w-[300px] h-[300px] bg-main-view-fg/5 rounded-xl flex items-center justify-center text-main-view-fg/40">
                Loading QR...
              </div>
            )}
            {relaySetupUrl && (
              <p className="text-xs text-main-view-fg/50 text-center">
                Or open the setup page on your phone browser
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ChatInput

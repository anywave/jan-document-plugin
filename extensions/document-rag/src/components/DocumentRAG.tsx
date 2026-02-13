/**
 * Document RAG Main Component
 * Integrates upload, library, and search functionality
 */

import React, { useState, useEffect } from 'react'
import { FileText, Search, Library, AlertCircle, Info, FolderTree } from 'lucide-react'
import { DocumentUpload } from './DocumentUpload'
import { DocumentLibrary } from './DocumentLibrary'
import { SearchInterface } from './SearchInterface'
import { XtractLib } from './XtractLib'
import { DocumentRAGErrorBoundary } from './DocumentRAGErrorBoundary'
import { checkPythonStatus, type PythonStatus } from '../python-bridge'
import { ensureQwenRegistered } from '../qwen-extraction'
import { toast } from 'sonner'

type Tab = 'upload' | 'library' | 'search' | 'xtract-lib'

interface DocumentRAGProps {
  defaultTab?: Tab
  collectionName?: string
  className?: string
}

export function DocumentRAG({
  defaultTab = 'upload',
  collectionName = 'documents',
  className = ''
}: DocumentRAGProps) {
  const [activeTab, setActiveTab] = useState<Tab>(defaultTab)
  const [pythonStatus, setPythonStatus] = useState<PythonStatus | null>(null)
  const [checkingPython, setCheckingPython] = useState(true)
  const [qwenAvailable, setQwenAvailable] = useState<boolean | null>(null)

  // Check Python status and Qwen model availability on mount
  useEffect(() => {
    const checkPython = async () => {
      try {
        const status = await checkPythonStatus()
        setPythonStatus(status)

        if (!status.available) {
          toast.error('Python not available. Please install Python 3.12+')
        } else if (status.error) {
          toast.warning(status.error)
        }
      } catch (error) {
        toast.error(`Failed to check Python: ${String(error)}`)
      } finally {
        setCheckingPython(false)
      }
    }

    const checkQwenModel = async () => {
      try {
        // Attempt to register Qwen if not already registered, then check availability
        const registered = await ensureQwenRegistered()
        setQwenAvailable(registered)
      } catch {
        setQwenAvailable(false)
      }
    }

    checkPython()
    checkQwenModel()
  }, [])

  // Show loading state while checking Python
  if (checkingPython) {
    return (
      <div className={`flex items-center justify-center p-12 ${className}`}>
        <div className="text-center space-y-3">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-sm text-muted-fg">Checking Python environment...</p>
        </div>
      </div>
    )
  }

  // Show error state if Python not available
  if (pythonStatus && !pythonStatus.available) {
    return (
      <div className={`p-6 rounded-lg border border-destructive/50 bg-destructive/10 ${className}`}>
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
          <div className="space-y-2">
            <h3 className="font-semibold text-destructive">Python Not Available</h3>
            <p className="text-sm text-destructive/90">
              {pythonStatus.error || 'Python 3.12+ is required for document processing.'}
            </p>
            <div className="text-sm space-y-1 text-destructive/80">
              <p><strong>To fix this:</strong></p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>Install Python 3.12 or later from python.org</li>
                <li>Add Python to your system PATH</li>
                <li>Restart MOBIUS</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <DocumentRAGErrorBoundary>
      <div className={`space-y-4 ${className}`}>
        {/* Tab Navigation */}
        <div className="border-b border-border">
          <div className="flex gap-1">
            <TabButton
              active={activeTab === 'upload'}
              onClick={() => setActiveTab('upload')}
              icon={<FileText className="h-4 w-4" />}
              label="Upload"
            />
            <TabButton
              active={activeTab === 'library'}
              onClick={() => setActiveTab('library')}
              icon={<Library className="h-4 w-4" />}
              label="Library"
            />
            <TabButton
              active={activeTab === 'search'}
              onClick={() => setActiveTab('search')}
              icon={<Search className="h-4 w-4" />}
              label="Search"
            />
            <TabButton
              active={activeTab === 'xtract-lib'}
              onClick={() => setActiveTab('xtract-lib')}
              icon={<FolderTree className="h-4 w-4" />}
              label="Xtract Lib"
            />
          </div>
        </div>

        {/* Status Badges */}
        <div className="flex items-center gap-4">
          {pythonStatus && pythonStatus.version && (
            <div className="flex items-center gap-2 text-xs text-muted-fg">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span>Python {pythonStatus.version.replace('Python ', '')}</span>
            </div>
          )}

          {qwenAvailable === false && (
            <div className="flex items-center gap-2 text-xs text-amber-600">
              <Info className="h-3 w-3" />
              <span>Qwen extraction model not found — RAG will use raw document chunks</span>
            </div>
          )}
        </div>

        {/* Tab Content */}
        <div className="min-h-[400px]">
          {activeTab === 'upload' && (
            <DocumentUpload
              collectionName={collectionName}
              onUploadComplete={() => {
                // Optionally switch to library after upload
                toast.success('Document indexed! View in Library tab.')
              }}
            />
          )}

          {activeTab === 'library' && (
            <DocumentLibrary
              collectionName={collectionName}
              onDocumentSelect={(doc) => {
                // Document selection handled by DocumentLibrary
              }}
            />
          )}

          {activeTab === 'search' && (
            <SearchInterface collectionName={collectionName} />
          )}

          {activeTab === 'xtract-lib' && (
            <XtractLib collectionName={collectionName} />
          )}
        </div>

        {/* Footer Info */}
        <div className="text-xs text-muted-fg text-center pt-4 border-t border-border">
          <p>
            Document RAG powered by Python • All processing happens locally • 100% offline
          </p>
        </div>
      </div>
    </DocumentRAGErrorBoundary>
  )
}

interface TabButtonProps {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-2 px-4 py-2 border-b-2 transition-colors font-medium text-sm
        ${active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-fg hover:text-fg hover:border-border'
        }
      `}
    >
      {icon}
      {label}
    </button>
  )
}

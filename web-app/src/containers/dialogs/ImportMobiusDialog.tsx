/**
 * Import .mobius package dialog — preview contents, show model warnings,
 * selective import of assistants/threads/knowledge.
 */

import { useState, useEffect } from 'react'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { Button } from '@/components/ui/button'
import {
  DialogClose,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import { IconAlertTriangle } from '@tabler/icons-react'

type Props = {
  /** If provided, skip file picker and preview this path directly */
  packagePath?: string
  onClose: () => void
  onImported?: () => void
}

export default function ImportMobiusDialog({
  packagePath: initialPath,
  onClose,
  onImported,
}: Props) {
  const { t } = useTranslation()

  const [preview, setPreview] = useState<MobiusImportPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filePath, setFilePath] = useState<string | null>(initialPath || null)

  // Selection state
  const [selectedAssistants, setSelectedAssistants] = useState<Set<string>>(
    new Set()
  )
  const [selectedThreads, setSelectedThreads] = useState<Set<string>>(
    new Set()
  )
  const [selectedKnowledge, setSelectedKnowledge] = useState<Set<string>>(
    new Set()
  )

  // On mount, pick file and preview
  useEffect(() => {
    const load = async () => {
      try {
        const { pickAndPreviewPackage, previewPackage } = await import(
          '@/lib/sharing/importPackage'
        )

        let result: MobiusImportPreview | null
        if (initialPath) {
          result = await previewPackage(initialPath)
        } else {
          result = await pickAndPreviewPackage()
        }

        if (!result) {
          onClose()
          return
        }

        setPreview(result)
        setFilePath(initialPath || (result as unknown as { packagePath?: string }).packagePath || '')

        // Select all by default
        setSelectedAssistants(new Set(result.assistants.map((a) => a.id)))
        setSelectedThreads(new Set(result.threads.map((t) => t.id)))
        setSelectedKnowledge(
          new Set(result.knowledge.map((k) => k.collection))
        )
      } catch (err) {
        setError(String(err))
      } finally {
        setLoading(false)
      }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const toggleAssistant = (id: string) => {
    setSelectedAssistants((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleThread = (id: string) => {
    setSelectedThreads((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleKnowledge = (collection: string) => {
    setSelectedKnowledge((prev) => {
      const next = new Set(prev)
      if (next.has(collection)) next.delete(collection)
      else next.add(collection)
      return next
    })
  }

  const canImport =
    selectedAssistants.size > 0 ||
    selectedThreads.size > 0 ||
    selectedKnowledge.size > 0

  const handleImport = async () => {
    if (!filePath) return
    setImporting(true)
    try {
      const { importFromPackage } = await import('@/lib/sharing/importPackage')
      const result = await importFromPackage({
        packagePath: filePath,
        assistantIds: Array.from(selectedAssistants),
        threadIds: Array.from(selectedThreads),
        knowledgeCollections: Array.from(selectedKnowledge),
      })

      const parts: string[] = []
      if (result.importedAssistants > 0)
        parts.push(`${result.importedAssistants} assistant${result.importedAssistants !== 1 ? 's' : ''}`)
      if (result.importedThreads > 0)
        parts.push(`${result.importedThreads} thread${result.importedThreads !== 1 ? 's' : ''}`)
      if (result.importedKnowledgeChunks > 0)
        parts.push(`${result.importedKnowledgeChunks} knowledge chunk${result.importedKnowledgeChunks !== 1 ? 's' : ''}`)

      toast.success(
        t('sharing:importSuccess', { items: parts.join(', ') }),
        { id: 'mobius-import' }
      )
      onImported?.()
      onClose()
    } catch (err) {
      console.error('Import failed:', err)
      toast.error(t('sharing:importFailed'), { id: 'mobius-import-error' })
    } finally {
      setImporting(false)
    }
  }

  if (loading) {
    return (
      <DialogHeader>
        <DialogTitle>{t('sharing:importTitle')}</DialogTitle>
        <DialogDescription>{t('common:loading')}</DialogDescription>
      </DialogHeader>
    )
  }

  if (error) {
    return (
      <>
        <DialogHeader>
          <DialogTitle>{t('sharing:importTitle')}</DialogTitle>
          <DialogDescription className="text-destructive">
            {error}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4">
          <DialogClose asChild>
            <Button size="sm">{t('common:close')}</Button>
          </DialogClose>
        </DialogFooter>
      </>
    )
  }

  if (!preview) return null

  return (
    <>
      <DialogHeader>
        <DialogTitle>{t('sharing:importTitle')}</DialogTitle>
        <DialogDescription>
          {preview.manifest.name}
          {preview.manifest.description && ` — ${preview.manifest.description}`}
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-col gap-3 mt-3 max-h-80 overflow-y-auto">
        {/* Model warnings */}
        {preview.modelWarnings.length > 0 && (
          <div className="flex items-start gap-2 p-2 bg-yellow-500/10 rounded text-sm">
            <IconAlertTriangle
              size={16}
              className="text-yellow-500 shrink-0 mt-0.5"
            />
            <div>
              <span className="font-medium">
                {t('sharing:modelWarningTitle')}
              </span>
              <ul className="mt-1 text-xs text-main-view-fg/70">
                {preview.modelWarnings.map((model) => (
                  <li key={model}>{model}</li>
                ))}
              </ul>
              <p className="mt-1 text-xs text-main-view-fg/60">
                {t('sharing:modelWarningDesc')}
              </p>
            </div>
          </div>
        )}

        {/* Assistants */}
        {preview.assistants.length > 0 && (
          <div>
            <span className="text-xs font-semibold text-main-view-fg/50 block mb-1">
              {t('common:assistants')} ({preview.assistants.length})
            </span>
            <div className="flex flex-col gap-1">
              {preview.assistants.map((a) => (
                <label
                  key={a.id}
                  className="flex items-center gap-2 cursor-pointer text-sm hover:bg-main-view-fg/5 rounded px-1 py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedAssistants.has(a.id)}
                    onChange={() => toggleAssistant(a.id)}
                    className="accent-left-panel-fg"
                  />
                  <span>{a.avatar}</span>
                  <span className="truncate">{a.name}</span>
                  {a.description && (
                    <span className="text-xs text-main-view-fg/50 truncate">
                      — {a.description}
                    </span>
                  )}
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Threads */}
        {preview.threads.length > 0 && (
          <div>
            <span className="text-xs font-semibold text-main-view-fg/50 block mb-1">
              Threads ({preview.threads.length})
            </span>
            <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
              {preview.threads.map((thread) => (
                <label
                  key={thread.id}
                  className="flex items-center gap-2 cursor-pointer text-sm hover:bg-main-view-fg/5 rounded px-1 py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedThreads.has(thread.id)}
                    onChange={() => toggleThread(thread.id)}
                    className="accent-left-panel-fg"
                  />
                  <span className="truncate">{thread.title}</span>
                  <span className="text-xs text-main-view-fg/40 shrink-0">
                    {thread.messageCount} msg{thread.messageCount !== 1 ? 's' : ''}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Knowledge */}
        {preview.knowledge.length > 0 && (
          <div>
            <span className="text-xs font-semibold text-main-view-fg/50 block mb-1">
              Knowledge ({preview.knowledge.length} collection
              {preview.knowledge.length !== 1 ? 's' : ''})
            </span>
            <div className="flex flex-col gap-1">
              {preview.knowledge.map((k) => (
                <label
                  key={k.collection}
                  className="flex items-center gap-2 cursor-pointer text-sm hover:bg-main-view-fg/5 rounded px-1 py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedKnowledge.has(k.collection)}
                    onChange={() => toggleKnowledge(k.collection)}
                    className="accent-left-panel-fg"
                  />
                  <span className="truncate">{k.collection}</span>
                  <span className="text-xs text-main-view-fg/40 shrink-0">
                    {k.chunkCount} chunk{k.chunkCount !== 1 ? 's' : ''}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      <DialogFooter className="mt-4">
        <DialogClose asChild>
          <Button variant="link" size="sm" className="hover:no-underline">
            {t('common:cancel')}
          </Button>
        </DialogClose>
        <Button
          size="sm"
          disabled={!canImport || importing}
          onClick={handleImport}
        >
          {importing
            ? t('sharing:importing')
            : t('sharing:import')}
        </Button>
      </DialogFooter>
    </>
  )
}

/**
 * Export .mobius package dialog — bundle export with checkboxes
 * for assistants, threads, and knowledge.
 */

import { useState, useMemo } from 'react'
import { useAssistant } from '@/hooks/useAssistant'
import { useThreads } from '@/hooks/useThreads'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { Button } from '@/components/ui/button'
import {
  DialogClose,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { toast } from 'sonner'

type Props = {
  /** Pre-selected thread IDs (from bulk select) */
  preSelectedThreadIds?: string[]
  /** Pre-selected assistant ID (from assistant context) */
  preSelectedAssistantId?: string
  onClose: () => void
}

export default function ExportMobiusDialog({
  preSelectedThreadIds = [],
  preSelectedAssistantId,
  onClose,
}: Props) {
  const { t } = useTranslation()
  const { assistants } = useAssistant()
  const { threads } = useThreads()
  const allThreads = useMemo(
    () => Object.values(threads).filter((t) => !t.isArchived),
    [threads]
  )

  // State
  const [packageName, setPackageName] = useState(
    preSelectedAssistantId
      ? assistants.find((a) => a.id === preSelectedAssistantId)?.name || 'Export'
      : preSelectedThreadIds.length === 1
        ? allThreads.find((t) => t.id === preSelectedThreadIds[0])?.title || 'Export'
        : 'MOBIUS Export'
  )
  const [description, setDescription] = useState('')
  const [includeInstructions, setIncludeInstructions] = useState(false)
  const [selectedAssistants, setSelectedAssistants] = useState<Set<string>>(
    new Set(preSelectedAssistantId ? [preSelectedAssistantId] : [])
  )
  const [selectedThreads, setSelectedThreads] = useState<Set<string>>(
    new Set(preSelectedThreadIds)
  )
  const [exporting, setExporting] = useState(false)

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

  const canExport =
    packageName.trim().length > 0 &&
    (selectedAssistants.size > 0 || selectedThreads.size > 0)

  const handleExport = async () => {
    setExporting(true)
    try {
      const { exportMobiusPackage } = await import('@/lib/sharing/exportPackage')
      const result = await exportMobiusPackage({
        name: packageName.trim(),
        description: description.trim() || undefined,
        assistantIds: Array.from(selectedAssistants),
        threadIds: Array.from(selectedThreads),
        knowledgeCollections: [],
        includeInstructions,
      })

      if (result) {
        toast.success(t('sharing:exportSuccess'), { id: 'mobius-export' })
        onClose()
      }
    } catch (err) {
      console.error('Export failed:', err)
      toast.error(t('sharing:exportFailed'), { id: 'mobius-export-error' })
    } finally {
      setExporting(false)
    }
  }

  const itemCount = selectedAssistants.size + selectedThreads.size

  return (
    <>
      <DialogHeader>
        <DialogTitle>{t('sharing:exportTitle')}</DialogTitle>
        <DialogDescription>{t('sharing:exportDescription')}</DialogDescription>
      </DialogHeader>

      <div className="flex flex-col gap-3 mt-3 max-h-80 overflow-y-auto">
        {/* Package name */}
        <div>
          <label className="text-xs font-medium text-main-view-fg/70 mb-1 block">
            {t('sharing:packageName')}
          </label>
          <Input
            value={packageName}
            onChange={(e) => setPackageName(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            placeholder="My Export"
          />
        </div>

        {/* Description */}
        <div>
          <label className="text-xs font-medium text-main-view-fg/70 mb-1 block">
            {t('sharing:packageDescription')}
          </label>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            placeholder={t('sharing:descriptionPlaceholder')}
          />
        </div>

        {/* Include instructions toggle */}
        <div className="flex items-center justify-between py-1">
          <span className="text-sm">{t('sharing:includeInstructions')}</span>
          <Switch
            checked={includeInstructions}
            onCheckedChange={setIncludeInstructions}
          />
        </div>

        {/* Assistants section */}
        {assistants.length > 0 && (
          <div>
            <span className="text-xs font-semibold text-main-view-fg/50 block mb-1">
              {t('common:assistants')} ({assistants.length})
            </span>
            <div className="flex flex-col gap-1">
              {assistants.map((a) => (
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
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Threads section */}
        {allThreads.length > 0 && (
          <div>
            <span className="text-xs font-semibold text-main-view-fg/50 block mb-1">
              Threads ({allThreads.length})
            </span>
            <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
              {allThreads.map((t) => (
                <label
                  key={t.id}
                  className="flex items-center gap-2 cursor-pointer text-sm hover:bg-main-view-fg/5 rounded px-1 py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedThreads.has(t.id)}
                    onChange={() => toggleThread(t.id)}
                    className="accent-left-panel-fg"
                  />
                  <span className="truncate">{t.title || 'Untitled'}</span>
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
          disabled={!canExport || exporting}
          onClick={handleExport}
        >
          {exporting
            ? t('sharing:exporting')
            : `${t('sharing:export')} (${itemCount})`}
        </Button>
      </DialogFooter>
    </>
  )
}

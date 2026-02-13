import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { MessageSquare, Bookmark, FileSearch, Volume2 } from 'lucide-react'
import { useClickOutside } from '@/hooks/useClickOutside'
import type { TextSelectionInfo } from '@/hooks/useTextSelection'

interface SelectionContextMenuProps {
  selection: TextSelectionInfo
  onSendToChat: () => void
  onSaveToXtractLib: () => void
  onSummarize: () => void
  onReadAloud: () => void
  onClose: () => void
}

export function SelectionContextMenu({
  selection,
  onSendToChat,
  onSaveToXtractLib,
  onSummarize,
  onReadAloud,
  onClose,
}: SelectionContextMenuProps) {
  const menuRef = useClickOutside<HTMLDivElement>(onClose)

  // Clamp position to viewport
  const { mouseX, mouseY, selectedText } = selection
  const menuWidth = 220
  const menuHeight = 140
  const x = Math.min(mouseX, window.innerWidth - menuWidth - 8)
  const y = Math.min(mouseY, window.innerHeight - menuHeight - 8)

  const wordCount = selectedText.split(/\s+/).filter(Boolean).length
  const charCount = selectedText.length
  const showSummarize = wordCount > 100 || charCount > 500

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return createPortal(
    <div
      ref={menuRef}
      className="fixed bg-main-view text-main-view-fg border border-main-view-fg/20 rounded-md shadow-md p-1 z-50"
      style={{ left: x, top: y }}
      data-ignore-outside-clicks
    >
      <MenuItem
        icon={<MessageSquare className="h-4 w-4" />}
        label="Send to Chat"
        onClick={() => { onSendToChat(); onClose() }}
      />
      <MenuItem
        icon={<Bookmark className="h-4 w-4" />}
        label="Save to Xtract Library"
        onClick={() => { onSaveToXtractLib(); onClose() }}
      />
      <MenuItem
        icon={<Volume2 className="h-4 w-4" />}
        label="Read Aloud"
        onClick={() => { onReadAloud(); onClose() }}
      />
      {showSummarize && (
        <MenuItem
          icon={<FileSearch className="h-4 w-4" />}
          label="Summarize"
          onClick={() => { onSummarize(); onClose() }}
        />
      )}
    </div>,
    document.body
  )
}

function MenuItem({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <div
      className="px-2 py-1.5 text-sm rounded-sm hover:bg-main-view-fg/10 cursor-pointer flex items-center gap-2"
      onClick={onClick}
    >
      {icon}
      {label}
    </div>
  )
}

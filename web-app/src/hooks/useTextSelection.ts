import { useCallback, useEffect, useState, RefObject } from 'react'

export interface TextSelectionInfo {
  selectedText: string
  mouseX: number
  mouseY: number
  messageId: string
  messageRole: string
  messageIndex: number
}

export function useTextSelection(containerRef: RefObject<HTMLElement | null>) {
  const [selection, setSelection] = useState<TextSelectionInfo | null>(null)

  const clearSelection = useCallback(() => {
    setSelection(null)
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleContextMenu = (e: MouseEvent) => {
      const sel = window.getSelection()
      const text = sel?.toString().trim()
      if (!text) return

      // Walk up from the target to find data-message-id
      let el = e.target as HTMLElement | null
      let messageId: string | null = null
      let messageRole = ''
      let messageIndex = -1

      while (el && el !== container) {
        if (el.dataset.messageId) {
          messageId = el.dataset.messageId
          messageRole = el.dataset.messageAuthorRole || ''
          messageIndex = parseInt(el.dataset.messageIndex || '-1', 10)
          break
        }
        el = el.parentElement
      }

      if (!messageId) return

      e.preventDefault()
      setSelection({
        selectedText: text,
        mouseX: e.clientX,
        mouseY: e.clientY,
        messageId,
        messageRole,
        messageIndex,
      })
    }

    container.addEventListener('contextmenu', handleContextMenu)
    return () => container.removeEventListener('contextmenu', handleContextMenu)
  }, [containerRef])

  return { selection, clearSelection }
}

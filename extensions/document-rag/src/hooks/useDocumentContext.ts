/**
 * Document Context Hook
 * Manages document context for chat integration
 */

import { create } from 'zustand'

export interface DocumentContextItem {
  /** Document source file path */
  source: string
  /** Text content of the chunk */
  content: string
  /** Relevance score (0-1) */
  distance: number
  /** Chunk metadata */
  metadata?: Record<string, any>
}

interface DocumentContextState {
  /** Active document context for current thread */
  context: Map<string, DocumentContextItem[]>
  /** Set context for a thread */
  setContext: (threadId: string, items: DocumentContextItem[]) => void
  /** Add items to existing context */
  addToContext: (threadId: string, items: DocumentContextItem[]) => void
  /** Clear context for a thread */
  clearContext: (threadId: string) => void
  /** Get context for a thread */
  getContext: (threadId: string) => DocumentContextItem[]
  /** Format context as string for injection */
  formatContext: (threadId: string) => string
}

export const useDocumentContext = create<DocumentContextState>((set, get) => ({
  context: new Map(),

  setContext: (threadId, items) => {
    set((state) => {
      const newContext = new Map(state.context)
      newContext.set(threadId, items)
      return { context: newContext }
    })
  },

  addToContext: (threadId, items) => {
    set((state) => {
      const newContext = new Map(state.context)
      const existing = newContext.get(threadId) || []
      // Avoid duplicates by source + content
      const combined = [...existing]
      items.forEach((item) => {
        const exists = existing.some(
          (e) => e.source === item.source && e.content === item.content
        )
        if (!exists) {
          combined.push(item)
        }
      })
      newContext.set(threadId, combined)
      return { context: newContext }
    })
  },

  clearContext: (threadId) => {
    set((state) => {
      const newContext = new Map(state.context)
      newContext.delete(threadId)
      return { context: newContext }
    })
  },

  getContext: (threadId) => {
    const state = get()
    return state.context.get(threadId) || []
  },

  formatContext: (threadId) => {
    const items = get().getContext(threadId)
    if (items.length === 0) return ''

    // Format as structured context
    const formattedItems = items
      .map((item, index) => {
        const score = Math.round((1 - item.distance) * 100)
        return `[Document ${index + 1}] ${item.source} (${score}% relevant)
${item.content.trim()}`
      })
      .join('\n\n')

    return `<document_context>
The following information has been retrieved from your documents to help answer your question:

${formattedItems}

Please use this context when relevant to the user's question. Cite sources when you reference information from these documents.
</document_context>`
  },
}))

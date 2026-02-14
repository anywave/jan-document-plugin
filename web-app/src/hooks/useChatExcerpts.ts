import { create } from 'zustand'
import { ulid } from 'ulidx'
import { localStorageKey } from '@/constants/localStorage'

export interface ChatExcerpt {
  id: string
  threadId: string
  messageId: string
  highlightText: string
  fullMessage: string
  assistantName: string
  timestamp: number
  inputPrompt: string | null
  createdAt: number
}

export interface Annotation {
  id: string
  threadId: string
  messageId: string
  sourceText: string
  summary: string
  createdAt: number
}

const MAX_EXCERPTS = 200
const MAX_FULL_MESSAGE_LENGTH = 10000

interface PersistedState {
  excerpts: ChatExcerpt[]
  annotations: Annotation[]
}

function loadFromStorage(): PersistedState {
  try {
    const raw = localStorage.getItem(localStorageKey.chatExcerpts)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        excerpts: Array.isArray(parsed.excerpts) ? parsed.excerpts : [],
        annotations: Array.isArray(parsed.annotations) ? parsed.annotations : [],
      }
    }
  } catch {
    // ignore parse errors
  }
  return { excerpts: [], annotations: [] }
}

function saveToStorage(state: PersistedState) {
  try {
    localStorage.setItem(localStorageKey.chatExcerpts, JSON.stringify(state))
  } catch {
    // Quota exceeded — trim oldest excerpts and retry
    const trimmed: PersistedState = {
      excerpts: state.excerpts.slice(0, Math.floor(state.excerpts.length / 2)),
      annotations: state.annotations,
    }
    try {
      localStorage.setItem(localStorageKey.chatExcerpts, JSON.stringify(trimmed))
    } catch {
      // Still failing — clear excerpts entirely to recover
      try {
        localStorage.setItem(
          localStorageKey.chatExcerpts,
          JSON.stringify({ excerpts: [], annotations: state.annotations })
        )
      } catch {
        // Storage completely full — nothing we can do
      }
    }
  }
}

interface ChatExcerptsState {
  excerpts: ChatExcerpt[]
  annotations: Annotation[]

  addExcerpt: (params: Omit<ChatExcerpt, 'id' | 'createdAt'>) => void
  removeExcerpt: (id: string) => void
  getExcerptsByThread: (threadId: string) => ChatExcerpt[]

  addAnnotation: (params: Omit<Annotation, 'id' | 'createdAt'>) => void
  removeAnnotation: (id: string) => void
  getAnnotationsByThread: (threadId: string) => Annotation[]
  getAnnotationForMessage: (messageId: string) => Annotation | undefined
}

const initial = loadFromStorage()

export const useChatExcerpts = create<ChatExcerptsState>((set, get) => ({
  excerpts: initial.excerpts,
  annotations: initial.annotations,

  addExcerpt: (params) => {
    const excerpt: ChatExcerpt = {
      ...params,
      id: ulid(),
      createdAt: Date.now(),
      fullMessage: params.fullMessage.slice(0, MAX_FULL_MESSAGE_LENGTH),
    }
    set((state) => {
      let next = [excerpt, ...state.excerpts]
      if (next.length > MAX_EXCERPTS) {
        next = next.slice(0, MAX_EXCERPTS)
      }
      const newState = { excerpts: next, annotations: state.annotations }
      saveToStorage(newState)
      return newState
    })
  },

  removeExcerpt: (id) => {
    set((state) => {
      const next = state.excerpts.filter((e) => e.id !== id)
      const newState = { excerpts: next, annotations: state.annotations }
      saveToStorage(newState)
      return newState
    })
  },

  getExcerptsByThread: (threadId) => {
    return get().excerpts.filter((e) => e.threadId === threadId)
  },

  addAnnotation: (params) => {
    const annotation: Annotation = {
      ...params,
      id: ulid(),
      createdAt: Date.now(),
    }
    set((state) => {
      // One annotation per message — replace if exists
      const filtered = state.annotations.filter(
        (a) => a.messageId !== params.messageId
      )
      const next = [annotation, ...filtered]
      const newState = { excerpts: state.excerpts, annotations: next }
      saveToStorage(newState)
      return newState
    })
  },

  removeAnnotation: (id) => {
    set((state) => {
      const next = state.annotations.filter((a) => a.id !== id)
      const newState = { excerpts: state.excerpts, annotations: next }
      saveToStorage(newState)
      return newState
    })
  },

  getAnnotationsByThread: (threadId) => {
    return get().annotations.filter((a) => a.threadId === threadId)
  },

  getAnnotationForMessage: (messageId) => {
    return get().annotations.find((a) => a.messageId === messageId)
  },
}))

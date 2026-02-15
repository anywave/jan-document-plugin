import { create } from 'zustand'

type PromptStoreState = {
  prompt: string
  setPrompt: (value: string | ((prev: string) => string)) => void
  resetPrompt: () => void
}

export const usePrompt = create<PromptStoreState>((set, get) => ({
  prompt: '',
  setPrompt: (value) =>
    set({ prompt: typeof value === 'function' ? value(get().prompt) : value }),
  resetPrompt: () => set({ prompt: '' }),
}))

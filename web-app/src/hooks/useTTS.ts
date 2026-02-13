import { create } from 'zustand'
import { localStorageKey } from '@/constants/localStorage'

export interface VoiceProfile {
  id: string
  displayName: string
  /** Substring to match against SAPI voice name/id */
  sapiVoice: string
  locale: string
  gender: 'Female' | 'Male'
  rate: number   // SAPI rate: 100=slow, 150=normal, 200=fast
}

/**
 * Built-in voice personas.
 * sapiVoice is matched against installed SAPI voices (substring, case-insensitive).
 * tts_engine.py prefers "Desktop" SAPI voices over OneCore stubs.
 * Catherine auto-activates once en-AU speech pack is installed via Windows Settings.
 */
export const VOICE_PROFILES: VoiceProfile[] = [
  {
    id: 'catherine',
    displayName: 'Microsoft Catherine',
    sapiVoice: 'Catherine',
    locale: 'en-AU',
    gender: 'Female',
    rate: 150,
  },
  {
    id: 'james',
    displayName: 'Microsoft James',
    sapiVoice: 'James',
    locale: 'en-AU',
    gender: 'Male',
    rate: 150,
  },
  {
    id: 'david',
    displayName: 'Microsoft David',
    sapiVoice: 'David',
    locale: 'en-US',
    gender: 'Male',
    rate: 150,
  },
  {
    id: 'zira',
    displayName: 'Microsoft Zira',
    sapiVoice: 'Zira',
    locale: 'en-US',
    gender: 'Female',
    rate: 150,
  },
]

/** Sanitize a string for use in filenames */
function sanitizeFilename(str: string): string {
  return str
    .replace(/[^a-zA-Z0-9 _-]/g, '')
    .replace(/\s+/g, '_')
    .slice(0, 60)
}

/** Generate an auto-name following the Xtract Library pattern */
export function generateTTSFilename(params: {
  threadTitle?: string
  voiceDisplayName: string
  textPreview?: string
}): string {
  const { threadTitle, voiceDisplayName, textPreview } = params
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const voicePart = sanitizeFilename(voiceDisplayName)

  if (threadTitle) {
    const titlePart = sanitizeFilename(threadTitle)
    return `${titlePart}-${voicePart}-${timestamp}.wav`
  }

  if (textPreview) {
    const previewPart = sanitizeFilename(textPreview.slice(0, 30))
    return `${previewPart}-${voicePart}-${timestamp}.wav`
  }

  return `reading-${voicePart}-${timestamp}.wav`
}

interface TTSState {
  selectedVoiceId: string
  isPlaying: boolean
  isGenerating: boolean
  audioElement: HTMLAudioElement | null
  lastGeneratedPath: string | null
  currentText: string | null

  setSelectedVoice: (id: string) => void
  getSelectedVoice: () => VoiceProfile
  play: (text: string, threadTitle?: string) => Promise<void>
  stop: () => void
  saveLastAsFile: (suggestedName?: string) => Promise<void>
}

function loadVoicePreference(): string {
  try {
    return localStorage.getItem(localStorageKey.ttsVoice) || 'catherine'
  } catch {
    return 'sovereign'
  }
}

export const useTTS = create<TTSState>((set, get) => ({
  selectedVoiceId: loadVoicePreference(),
  isPlaying: false,
  isGenerating: false,
  audioElement: null,
  lastGeneratedPath: null,
  currentText: null,

  setSelectedVoice: (id) => {
    set({ selectedVoiceId: id })
    try {
      localStorage.setItem(localStorageKey.ttsVoice, id)
    } catch {
      // ignore
    }
  },

  getSelectedVoice: () => {
    const { selectedVoiceId } = get()
    return VOICE_PROFILES.find((v) => v.id === selectedVoiceId) || VOICE_PROFILES[0]
  },

  play: async (text, threadTitle) => {
    const state = get()
    // Stop any existing playback
    if (state.audioElement) {
      state.audioElement.pause()
      state.audioElement.src = ''
    }

    const voice = state.getSelectedVoice()
    set({ isGenerating: true, currentText: text, isPlaying: false })

    try {
      // Check if Tauri is available
      const isTauri = '__TAURI__' in window
      if (!isTauri) {
        // Fallback: use Web Speech API for non-Tauri environments
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.lang = voice.locale
        utterance.onend = () => set({ isPlaying: false, currentText: null })
        window.speechSynthesis.speak(utterance)
        set({ isGenerating: false, isPlaying: true })
        return
      }

      const { invoke, convertFileSrc } = await import('@tauri-apps/api/core')
      const { appDataDir } = await import('@tauri-apps/api/path')

      const dataDir = await appDataDir()
      const filename = generateTTSFilename({
        threadTitle,
        voiceDisplayName: voice.displayName,
        textPreview: text,
      })
      const outputPath = `${dataDir}tts\\${filename}`

      const result = await invoke<{
        success: boolean
        output_path?: string
        size_bytes?: number
        error?: string
      }>('synthesize_speech', {
        text,
        voice: voice.sapiVoice,
        outputPath,
        rate: voice.rate,
      })

      if (!result.success) {
        throw new Error(result.error || 'TTS synthesis failed')
      }

      // Play the generated WAV
      const audioUrl = convertFileSrc(result.output_path || outputPath)
      const audio = new Audio(audioUrl)
      audio.onended = () => set({ isPlaying: false, currentText: null })
      audio.onerror = () => set({ isPlaying: false, isGenerating: false, currentText: null })
      await audio.play()

      set({
        isGenerating: false,
        isPlaying: true,
        audioElement: audio,
        lastGeneratedPath: result.output_path || outputPath,
      })
    } catch (err) {
      console.error('TTS error:', err)
      set({ isGenerating: false, isPlaying: false, currentText: null })
      throw err
    }
  },

  stop: () => {
    const { audioElement } = get()
    if (audioElement) {
      audioElement.pause()
      audioElement.src = ''
    }
    window.speechSynthesis?.cancel()
    set({ isPlaying: false, audioElement: null, currentText: null })
  },

  saveLastAsFile: async (suggestedName) => {
    const { currentText } = get()

    try {
      const { save } = await import('@tauri-apps/plugin-dialog')

      const voice = get().getSelectedVoice()
      const defaultName = suggestedName || generateTTSFilename({
        voiceDisplayName: voice.displayName,
        textPreview: currentText || undefined,
      })
      const savePath = await save({
        defaultPath: defaultName,
        filters: [{ name: 'WAV Audio', extensions: ['wav'] }],
      })

      if (!savePath) return

      if (currentText) {
        const { invoke } = await import('@tauri-apps/api/core')
        const result = await invoke<{
          success: boolean
          error?: string
        }>('synthesize_speech', {
          text: currentText,
          voice: voice.sapiVoice,
          outputPath: savePath,
          rate: voice.rate,
        })
        if (!result.success) throw new Error(result.error || 'Save failed')
      }
    } catch (err) {
      console.error('Save dialog error:', err)
      throw err
    }
  },
}))

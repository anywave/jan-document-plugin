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

/**
 * Speaker-aware text parser.
 * Detects **Speaker:** patterns and splits text into voiced segments.
 * Each segment gets assigned a voice based on the speaker identity.
 */
export interface VoicedSegment {
  speaker: string    // 'narrator' or the detected speaker name
  text: string
  voice: VoiceProfile
}

function assignVoice(speaker: string, speakerMap: Map<string, VoiceProfile>, defaultVoice: VoiceProfile): VoiceProfile {
  const key = speaker.toLowerCase()
  if (speakerMap.has(key)) return speakerMap.get(key)!

  // Assign voices round-robin, alternating gender when possible
  const usedIds = new Set([...speakerMap.values()].map(v => v.id))
  const available = VOICE_PROFILES.filter(v => !usedIds.has(v.id))
  const pick = available.length > 0 ? available[0] : VOICE_PROFILES[speakerMap.size % VOICE_PROFILES.length]
  speakerMap.set(key, pick)
  return pick
}

export function parseMultiVoiceText(text: string, defaultVoice: VoiceProfile): VoicedSegment[] {
  const segments: VoicedSegment[] = []
  const speakerMap = new Map<string, VoiceProfile>()
  // Reserve the default voice for narrator
  speakerMap.set('narrator', defaultVoice)

  // Split by **Speaker:** markers
  const pattern = /\*\*([^*]+?):\*\*\s*/g
  const parts = text.split(pattern)

  // parts alternates: [before, speaker1, content1, speaker2, content2, ...]
  if (parts.length <= 1) {
    // No speaker markers found — single segment
    return [{ speaker: 'narrator', text: text.trim(), voice: defaultVoice }]
  }

  // First element is text before any speaker marker (narration)
  const preamble = parts[0].trim()
  if (preamble) {
    segments.push({ speaker: 'narrator', text: preamble, voice: defaultVoice })
  }

  // Process speaker/content pairs
  for (let i = 1; i < parts.length; i += 2) {
    const speakerName = parts[i]?.trim()
    const content = parts[i + 1]?.trim()
    if (speakerName && content) {
      const voice = assignVoice(speakerName, speakerMap, defaultVoice)
      segments.push({ speaker: speakerName, text: content, voice })
    }
  }

  if (segments.length === 0) {
    segments.push({ speaker: 'narrator', text: text.trim(), voice: defaultVoice })
  }

  return segments
}

/** Detect unique speaker names in text (for voice assignment UI) */
export function detectSpeakers(text: string): string[] {
  const pattern = /\*\*([^*]+?):\*\*/g
  const speakers = new Set<string>()
  const parts = text.split(pattern)
  for (let i = 1; i < parts.length; i += 2) {
    const name = parts[i]?.trim()
    if (name) speakers.add(name)
  }
  return [...speakers].slice(0, VOICE_PROFILES.length)
}

/** Build segments using explicit speaker→voice assignments from the user */
export function buildSegmentsWithAssignments(
  text: string,
  assignments: Record<string, string>,  // speaker name → voice profile id
  defaultVoice: VoiceProfile
): VoicedSegment[] {
  const segments: VoicedSegment[] = []
  const pattern = /\*\*([^*]+?):\*\*\s*/g
  const parts = text.split(pattern)

  if (parts.length <= 1) {
    return [{ speaker: 'narrator', text: text.trim(), voice: defaultVoice }]
  }

  const preamble = parts[0].trim()
  if (preamble) {
    segments.push({ speaker: 'narrator', text: preamble, voice: defaultVoice })
  }

  for (let i = 1; i < parts.length; i += 2) {
    const speakerName = parts[i]?.trim()
    const content = parts[i + 1]?.trim()
    if (speakerName && content) {
      const voiceId = assignments[speakerName]
      const voice = VOICE_PROFILES.find(v => v.id === voiceId) || defaultVoice
      segments.push({ speaker: speakerName, text: content, voice })
    }
  }

  if (segments.length === 0) {
    segments.push({ speaker: 'narrator', text: text.trim(), voice: defaultVoice })
  }

  return segments
}

/**
 * Glyph-to-speech map.
 * SAPI silently drops most Unicode symbols. Each glyph gets a phonetic
 * replacement wrapped in commas (SAPI pauses) to sustain ~1 second.
 * Exported so the shimmer animation can detect which chars are glyphs.
 */
export const GLYPH_SPEECH_MAP: Record<string, string> = {
  '\u22C8': ', ohm, ',    // ⋈ — bridge/join (resonant hum)
  '\u0394': ', delta, ',  // Δ
  '\u0398': ', theta, ',  // Θ
  '\u03A8': ', psi, ',    // Ψ
  '\u039E': ', xi, ',     // Ξ
  '\u03A3': ', sigma, ',  // Σ
  '\u03A6': ', phi, ',    // Φ
  '\u03A9': ', omega, ',  // Ω
  '\u2207': ', nabla, ',  // ∇
  '\u03C8': ', psi, ',    // ψ (lowercase)
  '\u21D4': ', ahh, ',    // ⇔ — biconditional
  '\u27F2': ', ahh, ',    // ⟲ — cycle
}

/** Characters that count as "glyphs" for shimmer animation */
export const GLYPH_CHARS = new Set(Object.keys(GLYPH_SPEECH_MAP))

/** Strip markdown and symbols that SAPI vocalizes as words */
function cleanForSpeech(text: string): string {
  // Replace glyphs with sustained phonetic sounds before stripping markdown
  let result = text
  for (const [glyph, phonetic] of Object.entries(GLYPH_SPEECH_MAP)) {
    result = result.split(glyph).join(phonetic)
  }

  return result
    .replace(/\*\*([^*]+)\*\*/g, '$1')   // **bold** → bold
    .replace(/\*([^*]+)\*/g, '$1')        // *italic* → italic
    .replace(/`([^`]+)`/g, '$1')          // `code` → code
    .replace(/^#{1,6}\s+/gm, '')          // # headings
    .replace(/^>\s+/gm, '')               // > blockquotes
    .replace(/^[-*+]\s+/gm, '')           // - bullet points
    .replace(/^\d+\.\s+/gm, '')           // 1. numbered lists
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [link](url) → link
    .replace(/["""]/g, '')                // curly and straight quotes
    .replace(/\|/g, '')                   // table pipes
    .replace(/---+/g, '')                 // horizontal rules
    .replace(/\n{2,}/g, '. ')             // paragraph breaks → pause
    .replace(/\n/g, ' ')                  // line breaks → space
    .replace(/\s{2,}/g, ' ')             // collapse whitespace
    .trim()
}

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

/** Pending voice assignment — shown to user before multi-voice playback */
export interface PendingAssignment {
  speakers: string[]
  text: string
  threadTitle?: string
  /** Default mapping: speaker name → voice profile id */
  defaults: Record<string, string>
}

interface TTSState {
  selectedVoiceId: string
  isPlaying: boolean
  isGenerating: boolean
  audioElement: HTMLAudioElement | null
  lastGeneratedPath: string | null
  currentText: string | null
  /** When set, UI should show voice assignment dialog */
  pendingAssignment: PendingAssignment | null

  setSelectedVoice: (id: string) => void
  getSelectedVoice: () => VoiceProfile
  play: (text: string, threadTitle?: string) => Promise<void>
  /** Play with explicit user-chosen voice assignments */
  playWithAssignments: (text: string, assignments: Record<string, string>, threadTitle?: string) => Promise<void>
  /** Dismiss the voice assignment dialog without playing */
  dismissAssignment: () => void
  stop: () => void
  saveLastAsFile: (suggestedName?: string) => Promise<void>
}

// --- Helper types for passing zustand's set/get to standalone functions ---
type ZuSet = (partial: Partial<TTSState>) => void
type ZuGet = () => TTSState

/** Synthesize a single-voice utterance and play it */
async function synthesizeAndPlay(
  _get: ZuGet,
  set: ZuSet,
  text: string,
  voice: VoiceProfile,
  threadTitle?: string
): Promise<void> {
  const isTauri = '__TAURI__' in window
  if (!isTauri) {
    const utterance = new SpeechSynthesisUtterance(cleanForSpeech(text))
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
    textPreview: text.slice(0, 30),
  })
  const outputPath = `${dataDir}tts\\${filename}`

  const result = await invoke<{
    success: boolean
    output_path?: string
    size_bytes?: number
    error?: string
  }>('synthesize_speech', {
    text: cleanForSpeech(text),
    voice: voice.sapiVoice,
    outputPath,
    rate: voice.rate,
  })

  if (!result.success || !result.output_path) {
    throw new Error(result.error || 'Synthesis failed')
  }

  set({ isGenerating: false, isPlaying: true, lastGeneratedPath: result.output_path })
  const audio = new Audio(convertFileSrc(result.output_path))
  audio.onended = () => set({ isPlaying: false, audioElement: null, currentText: null })
  audio.onerror = () => set({ isPlaying: false, audioElement: null, currentText: null })
  set({ audioElement: audio })
  audio.play()
}

/** Play a sequence of WAV files back-to-back (for multi-voice segments) */
function chainPlayback(
  paths: string[],
  convertFileSrc: (path: string) => string,
  set: ZuSet
): void {
  let index = 0

  function playNext() {
    if (index >= paths.length) {
      set({ isPlaying: false, audioElement: null, currentText: null })
      return
    }
    const audio = new Audio(convertFileSrc(paths[index]))
    audio.onended = () => {
      index++
      playNext()
    }
    audio.onerror = () => {
      set({ isPlaying: false, audioElement: null, currentText: null })
    }
    set({ audioElement: audio, lastGeneratedPath: paths[index] })
    audio.play()
  }

  playNext()
}

function loadVoicePreference(): string {
  try {
    return localStorage.getItem(localStorageKey.ttsVoice) || 'catherine'
  } catch {
    return 'catherine'
  }
}

export const useTTS = create<TTSState>((set, get) => ({
  selectedVoiceId: loadVoicePreference(),
  isPlaying: false,
  isGenerating: false,
  audioElement: null,
  lastGeneratedPath: null,
  currentText: null,
  pendingAssignment: null,

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
    if (state.audioElement) {
      state.audioElement.pause()
      state.audioElement.src = ''
    }

    const voice = state.getSelectedVoice()

    // Detect multiple speakers — if found, show assignment dialog
    const speakers = detectSpeakers(text)
    if (speakers.length > 1) {
      // Build default assignments: round-robin across available voices
      const defaults: Record<string, string> = {}
      speakers.forEach((speaker, i) => {
        defaults[speaker] = VOICE_PROFILES[i % VOICE_PROFILES.length].id
      })
      set({ pendingAssignment: { speakers, text, threadTitle, defaults } })
      return  // UI will call playWithAssignments after user picks voices
    }

    // Single speaker or narration — play directly
    set({ isGenerating: true, currentText: text, isPlaying: false })
    try {
      await synthesizeAndPlay(get, set, text, voice, threadTitle)
    } catch (err) {
      console.error('TTS error:', err)
      set({ isGenerating: false, isPlaying: false, currentText: null })
      throw err
    }
  },

  playWithAssignments: async (text, assignments, threadTitle) => {
    const state = get()
    if (state.audioElement) {
      state.audioElement.pause()
      state.audioElement.src = ''
    }

    const defaultVoice = state.getSelectedVoice()
    set({ isGenerating: true, currentText: text, isPlaying: false, pendingAssignment: null })

    try {
      const isTauri = '__TAURI__' in window
      if (!isTauri) {
        const utterance = new SpeechSynthesisUtterance(cleanForSpeech(text))
        utterance.lang = defaultVoice.locale
        utterance.onend = () => set({ isPlaying: false, currentText: null })
        window.speechSynthesis.speak(utterance)
        set({ isGenerating: false, isPlaying: true })
        return
      }

      const { invoke, convertFileSrc } = await import('@tauri-apps/api/core')
      const { appDataDir } = await import('@tauri-apps/api/path')
      const dataDir = await appDataDir()

      const segments = buildSegmentsWithAssignments(text, assignments, defaultVoice)
      const audioPaths: string[] = []

      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i]
        const filename = `tts_seg_${i}_${sanitizeFilename(seg.speaker)}.wav`
        const outputPath = `${dataDir}tts\\${filename}`

        const result = await invoke<{
          success: boolean
          output_path?: string
          size_bytes?: number
          error?: string
        }>('synthesize_speech', {
          text: cleanForSpeech(seg.text),
          voice: seg.voice.sapiVoice,
          outputPath,
          rate: seg.voice.rate,
        })

        if (result.success && result.output_path) {
          audioPaths.push(result.output_path)
        }
      }

      if (audioPaths.length === 0) throw new Error('No audio segments generated')

      set({ isGenerating: false, isPlaying: true })
      chainPlayback(audioPaths, convertFileSrc, set)

    } catch (err) {
      console.error('TTS error:', err)
      set({ isGenerating: false, isPlaying: false, currentText: null })
      throw err
    }
  },

  dismissAssignment: () => {
    set({ pendingAssignment: null })
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

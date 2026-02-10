/**
 * Text-to-Speech Hook
 * Uses Web Speech API for voice output
 */

import { useState, useEffect, useCallback, useRef } from 'react'

interface UseTextToSpeechOptions {
  /** Voice to use (default: system default) */
  voice?: SpeechSynthesisVoice
  /** Speech rate (0.1 - 10, default: 1) */
  rate?: number
  /** Speech pitch (0 - 2, default: 1) */
  pitch?: number
  /** Speech volume (0 - 1, default: 1) */
  volume?: number
  /** Language (default: 'en-US') */
  lang?: string
}

interface UseTextToSpeechReturn {
  /** Speak the given text */
  speak: (text: string) => void
  /** Stop speaking */
  stop: () => void
  /** Pause speaking */
  pause: () => void
  /** Resume speaking */
  resume: () => void
  /** Is currently speaking */
  isSpeaking: boolean
  /** Is paused */
  isPaused: boolean
  /** Is TTS supported */
  isSupported: boolean
  /** Available voices */
  voices: SpeechSynthesisVoice[]
  /** Set voice */
  setVoice: (voice: SpeechSynthesisVoice) => void
  /** Set rate */
  setRate: (rate: number) => void
  /** Set pitch */
  setPitch: (pitch: number) => void
  /** Set volume */
  setVolume: (volume: number) => void
}

export const useTextToSpeech = (
  options: UseTextToSpeechOptions = {}
): UseTextToSpeechReturn => {
  const {
    voice: initialVoice,
    rate: initialRate = 1,
    pitch: initialPitch = 1,
    volume: initialVolume = 1,
    lang = 'en-US',
  } = options

  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([])
  const [selectedVoice, setSelectedVoice] = useState<
    SpeechSynthesisVoice | undefined
  >(initialVoice)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [rate, setRateState] = useState(initialRate)
  const [pitch, setPitchState] = useState(initialPitch)
  const [volume, setVolumeState] = useState(initialVolume)

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  const isSupported = Boolean(window.speechSynthesis)

  // Load available voices
  useEffect(() => {
    if (!isSupported) return

    const loadVoices = () => {
      const availableVoices = window.speechSynthesis.getVoices()
      setVoices(availableVoices)

      // Auto-select first voice matching language if none selected
      if (!selectedVoice && availableVoices.length > 0) {
        const defaultVoice =
          availableVoices.find((v) => v.lang.startsWith(lang.split('-')[0])) ||
          availableVoices[0]
        setSelectedVoice(defaultVoice)
      }
    }

    loadVoices()

    // Voices may load asynchronously
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices
    }

    return () => {
      window.speechSynthesis.cancel()
    }
  }, [isSupported, lang, selectedVoice])

  const speak = useCallback(
    (text: string) => {
      if (!isSupported) {
        console.warn('Text-to-speech is not supported')
        return
      }

      // Cancel any ongoing speech
      window.speechSynthesis.cancel()

      const utterance = new SpeechSynthesisUtterance(text)
      utterance.voice = selectedVoice || null
      utterance.rate = rate
      utterance.pitch = pitch
      utterance.volume = volume
      utterance.lang = lang

      utterance.onstart = () => {
        setIsSpeaking(true)
        setIsPaused(false)
      }

      utterance.onend = () => {
        setIsSpeaking(false)
        setIsPaused(false)
      }

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event)
        setIsSpeaking(false)
        setIsPaused(false)
      }

      utterance.onpause = () => {
        setIsPaused(true)
      }

      utterance.onresume = () => {
        setIsPaused(false)
      }

      utteranceRef.current = utterance
      window.speechSynthesis.speak(utterance)
    },
    [isSupported, selectedVoice, rate, pitch, volume, lang]
  )

  const stop = useCallback(() => {
    if (isSupported) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      setIsPaused(false)
    }
  }, [isSupported])

  const pause = useCallback(() => {
    if (isSupported && isSpeaking) {
      window.speechSynthesis.pause()
      setIsPaused(true)
    }
  }, [isSupported, isSpeaking])

  const resume = useCallback(() => {
    if (isSupported && isPaused) {
      window.speechSynthesis.resume()
      setIsPaused(false)
    }
  }, [isSupported, isPaused])

  const setVoice = useCallback((voice: SpeechSynthesisVoice) => {
    setSelectedVoice(voice)
  }, [])

  const setRate = useCallback((newRate: number) => {
    setRateState(Math.max(0.1, Math.min(10, newRate)))
  }, [])

  const setPitch = useCallback((newPitch: number) => {
    setPitchState(Math.max(0, Math.min(2, newPitch)))
  }, [])

  const setVolume = useCallback((newVolume: number) => {
    setVolumeState(Math.max(0, Math.min(1, newVolume)))
  }, [])

  return {
    speak,
    stop,
    pause,
    resume,
    isSpeaking,
    isPaused,
    isSupported,
    voices,
    setVoice,
    setRate,
    setPitch,
    setVolume,
  }
}

/**
 * Speech Recognition Hook
 * Uses Web Speech API for voice input
 */

import { useState, useEffect, useRef, useCallback } from 'react'

// Browser compatibility check
const SpeechRecognition =
  window.SpeechRecognition || (window as any).webkitSpeechRecognition

interface UseSpeechRecognitionOptions {
  /** Language code (default: 'en-US') */
  lang?: string
  /** Continuous recognition (default: true) */
  continuous?: boolean
  /** Return interim results (default: true) */
  interimResults?: boolean
  /** Max alternative transcriptions (default: 1) */
  maxAlternatives?: number
}

interface UseSpeechRecognitionReturn {
  /** Current transcript */
  transcript: string
  /** Interim (not final) transcript */
  interimTranscript: string
  /** Is currently listening */
  isListening: boolean
  /** Is speech recognition supported */
  isSupported: boolean
  /** Start listening */
  startListening: () => void
  /** Stop listening */
  stopListening: () => void
  /** Toggle listening */
  toggleListening: () => void
  /** Reset transcript */
  resetTranscript: () => void
  /** Error message */
  error: string | null
}

export const useSpeechRecognition = (
  options: UseSpeechRecognitionOptions = {}
): UseSpeechRecognitionReturn => {
  const {
    lang = 'en-US',
    continuous = true,
    interimResults = true,
    maxAlternatives = 1,
  } = options

  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)

  const isSupported = Boolean(SpeechRecognition)

  // Initialize speech recognition
  useEffect(() => {
    if (!isSupported) {
      setError('Speech recognition is not supported in this browser')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = lang
    recognition.continuous = continuous
    recognition.interimResults = interimResults
    recognition.maxAlternatives = maxAlternatives

    recognition.onstart = () => {
      setIsListening(true)
      setError(null)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognition.onresult = (event: any) => {
      let interimText = ''
      let finalText = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const transcriptText = result[0].transcript

        if (result.isFinal) {
          finalText += transcriptText + ' '
        } else {
          interimText += transcriptText
        }
      }

      if (finalText) {
        setTranscript((prev) => prev + finalText)
        setInterimTranscript('')
      } else {
        setInterimTranscript(interimText)
      }
    }

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)

      switch (event.error) {
        case 'no-speech':
          setError('No speech detected. Please try again.')
          break
        case 'audio-capture':
          setError('No microphone found. Please check your microphone.')
          break
        case 'not-allowed':
          setError('Microphone access denied. Please allow microphone access.')
          break
        case 'network':
          setError('Network error. Please check your connection.')
          break
        default:
          setError(`Speech recognition error: ${event.error}`)
      }

      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [isSupported, lang, continuous, interimResults, maxAlternatives])

  const startListening = useCallback(() => {
    if (!isSupported) {
      setError('Speech recognition is not supported')
      return
    }

    if (recognitionRef.current && !isListening) {
      try {
        recognitionRef.current.start()
      } catch (err) {
        // Already started, ignore
        console.warn('Recognition already started')
      }
    }
  }, [isSupported, isListening])

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop()
    }
  }, [isListening])

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }, [isListening, startListening, stopListening])

  const resetTranscript = useCallback(() => {
    setTranscript('')
    setInterimTranscript('')
  }, [])

  return {
    transcript,
    interimTranscript,
    isListening,
    isSupported,
    startListening,
    stopListening,
    toggleListening,
    resetTranscript,
    error,
  }
}

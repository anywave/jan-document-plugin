/**
 * Voice Relay Hook
 * Connects to the MOBIUS Voice Relay WebSocket server to receive
 * phone-originated speech-to-text transcripts over Wi-Fi.
 *
 * The relay server runs locally (voice_relay.py) and bridges
 * the phone's native Web Speech API to the desktop MOBIUS instance.
 */

import { useState, useEffect, useRef, useCallback } from 'react'

const RELAY_PORT = 8089
const RECONNECT_DELAY = 5000

export interface UseVoiceRelayReturn {
  /** Latest transcript received from the phone */
  transcript: string
  /** Whether the WebSocket connection to the relay is open */
  isConnected: boolean
  /** URL for the phone setup page (with QR code) */
  setupUrl: string | null
  /** Connect to the voice relay server */
  connect: () => void
  /** Disconnect from the voice relay server */
  disconnect: () => void
  /** Clear the current transcript */
  resetTranscript: () => void
  /** Error message if connection failed */
  error: string | null
}

export const useVoiceRelay = (): UseVoiceRelayReturn => {
  const [transcript, setTranscript] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [setupUrl, setSetupUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const intentionalRef = useRef(false)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    intentionalRef.current = false
    setError(null)

    try {
      const ws = new WebSocket(`ws://localhost:${RELAY_PORT}/ws?role=desktop`)

      ws.onopen = () => {
        setIsConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          switch (data.type) {
            case 'voice_transcript':
              if (data.text) setTranscript(data.text)
              break
            case 'session_start':
              // Desktop connected — derive setup URL from connection
              setSetupUrl(`http://localhost:${RELAY_PORT}/setup`)
              break
          }
        } catch {
          // Non-JSON message, ignore
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null
        if (!intentionalRef.current) {
          reconnectRef.current = setTimeout(connect, RECONNECT_DELAY)
        }
      }

      ws.onerror = () => {
        setError('Voice relay not running')
        setIsConnected(false)
      }

      wsRef.current = ws
    } catch {
      setError('Failed to connect to voice relay')
    }
  }, [])

  const disconnect = useCallback(() => {
    intentionalRef.current = true
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current)
      reconnectRef.current = null
    }
    wsRef.current?.close()
    wsRef.current = null
    setIsConnected(false)
    setSetupUrl(null)
  }, [])

  const resetTranscript = useCallback(() => setTranscript(''), [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalRef.current = true
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [])

  return {
    transcript,
    isConnected,
    setupUrl,
    connect,
    disconnect,
    resetTranscript,
    error,
  }
}

import { create } from 'zustand'
import { callTool } from '@/services/mcp'
import { useCodexState } from './useCodexState'

/**
 * Coherence Glove — bridges MCP coherence engine state to the frontend.
 *
 * Polls the coherence-glove MCP server for state updates, sets a CSS
 * custom property (--coherence) on the document root to drive glyph
 * shimmer intensity, and optionally feeds Codex operator chain.
 *
 * Completely silent when the MCP server is offline — no errors, no UI trace.
 */

interface CoherenceGloveState {
  connected: boolean
  scalarCoherence: number
  intentionality: number
  breathEntrained: boolean
  consentLevel: string
  bandAmplitudes: number[]
  dominantBand: string
  lastUpdate: number | null

  // Actions
  pollState: () => Promise<void>
  pushText: (text: string) => Promise<void>
  startPolling: () => void
  stopPolling: () => void
}

let pollInterval: ReturnType<typeof setInterval> | null = null

const useCoherenceGlove = create<CoherenceGloveState>((set, get) => ({
  connected: false,
  scalarCoherence: 0,
  intentionality: 0,
  breathEntrained: false,
  consentLevel: 'SUSPENDED',
  bandAmplitudes: [0, 0, 0, 0, 0],
  dominantBand: 'CORE',
  lastUpdate: null,

  pollState: async () => {
    try {
      const result = await callTool({
        toolName: 'coherence_get_state',
        arguments: {},
      })

      if (result?.error || !result?.content?.[0]?.text) {
        set({ connected: false })
        document.documentElement.style.setProperty('--coherence', '0')
        return
      }

      const state = JSON.parse(result.content[0].text)
      if (state.error) {
        set({ connected: false })
        document.documentElement.style.setProperty('--coherence', '0')
        return
      }

      const scalar = state.scalarCoherence ?? 0
      set({
        connected: true,
        scalarCoherence: scalar,
        intentionality: state.intentionality ?? 0,
        breathEntrained: state.breathEntrained ?? false,
        consentLevel: state.consentLevel ?? 'SUSPENDED',
        bandAmplitudes: state.bandAmplitudes ?? [0, 0, 0, 0, 0],
        dominantBand: state.dominantBand ?? 'CORE',
        lastUpdate: Date.now(),
      })

      // Drive CSS variable for glyph shimmer
      document.documentElement.style.setProperty(
        '--coherence',
        String(scalar)
      )

      // Wire to Codex operator chain
      const codex = useCodexState.getState()
      // CORE band → xi operator (bridge equation)
      codex.updateCoherence('xi', state.bandAmplitudes?.[2] ?? 0)
      // Scalar coherence → psiLoop (overall fidelity)
      codex.updateCoherence('psiLoop', scalar)
      // Intentionality → radix (breath-driven awareness)
      codex.updateCoherence('radix', state.intentionality ?? 0)
    } catch {
      // Server offline — degrade silently
      if (get().connected) {
        set({ connected: false })
        document.documentElement.style.setProperty('--coherence', '0')
      }
    }
  },

  pushText: async (text: string) => {
    try {
      const result = await callTool({
        toolName: 'coherence_push_text',
        arguments: { text },
      })

      if (result?.content?.[0]?.text) {
        const state = JSON.parse(result.content[0].text)
        if (!state.error) {
          const scalar = state.scalarCoherence ?? 0
          set({
            connected: true,
            scalarCoherence: scalar,
            intentionality: state.intentionality ?? 0,
            breathEntrained: state.breathEntrained ?? false,
            consentLevel: state.consentLevel ?? 'SUSPENDED',
            bandAmplitudes: state.bandAmplitudes ?? [0, 0, 0, 0, 0],
            dominantBand: state.dominantBand ?? 'CORE',
            lastUpdate: Date.now(),
          })
          document.documentElement.style.setProperty(
            '--coherence',
            String(scalar)
          )
        }
      }
    } catch {
      // Silent failure
    }
  },

  startPolling: () => {
    if (pollInterval) return
    // Initial poll
    get().pollState()
    // Then every 5 seconds
    pollInterval = setInterval(() => {
      get().pollState()
    }, 5000)
  },

  stopPolling: () => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    set({ connected: false })
    document.documentElement.style.setProperty('--coherence', '0')
  },
}))

export { useCoherenceGlove }

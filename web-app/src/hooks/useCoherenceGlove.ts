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
 * Manages biometric sensor subprocesses (breath mic, camera PPG)
 * via MCP tool calls.
 *
 * Completely silent when the MCP server is offline — no errors, no UI trace.
 */

interface SensorInfo {
  name: string
  exists: boolean
  running: boolean
}

interface CoherenceGloveState {
  connected: boolean
  scalarCoherence: number
  intentionality: number
  breathEntrained: boolean
  consentLevel: string
  bandAmplitudes: number[]
  dominantBand: string
  lastUpdate: number | null

  // Sensor state
  sensors: SensorInfo[]
  sensorLoading: boolean

  // Session state
  sessionActive: boolean
  sessionPhase: string
  promptCount: number
  tokenEstimate: number
  showSubjectivePrompt: boolean
  subjectivePromptSource: 'mid_session' | 'end_session'

  // Actions
  pollState: () => Promise<void>
  pushText: (text: string) => Promise<void>
  startPolling: () => void
  stopPolling: () => void
  startSensor: (name: string) => Promise<void>
  stopSensor: (name: string) => Promise<void>
  refreshSensors: () => Promise<void>

  // Session actions
  startSession: () => Promise<void>
  endSession: () => Promise<void>
  dismissSubjectivePrompt: () => void
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

  sensors: [],
  sensorLoading: false,

  sessionActive: false,
  sessionPhase: 'dissolve',
  promptCount: 0,
  tokenEstimate: 0,
  showSubjectivePrompt: false,
  subjectivePromptSource: 'mid_session' as const,

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

      let state: Record<string, unknown>
      try {
        state = JSON.parse(result.content[0].text)
      } catch {
        set({ connected: false })
        document.documentElement.style.setProperty('--coherence', '0')
        return
      }

      if (state.error) {
        set({ connected: false })
        document.documentElement.style.setProperty('--coherence', '0')
        return
      }

      const scalar = (state.scalarCoherence as number) ?? 0
      set({
        connected: true,
        scalarCoherence: scalar,
        intentionality: (state.intentionality as number) ?? 0,
        breathEntrained: (state.breathEntrained as boolean) ?? false,
        consentLevel: (state.consentLevel as string) ?? 'SUSPENDED',
        bandAmplitudes: (state.bandAmplitudes as number[]) ?? [0, 0, 0, 0, 0],
        dominantBand: (state.dominantBand as string) ?? 'CORE',
        lastUpdate: Date.now(),
      })

      // Drive CSS variable for glyph shimmer
      document.documentElement.style.setProperty(
        '--coherence',
        String(scalar)
      )

      // Wire to Codex operator chain
      const codex = useCodexState.getState()
      if (codex?.updateCoherence) {
        // CORE band → xi operator (bridge equation)
        codex.updateCoherence('xi', (state.bandAmplitudes as number[])?.[2] ?? 0)
        // Scalar coherence → psiLoop (overall fidelity)
        codex.updateCoherence('psiLoop', scalar)
        // Intentionality → radix (breath-driven awareness)
        codex.updateCoherence('radix', (state.intentionality as number) ?? 0)
      }
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
        let state: Record<string, unknown>
        try {
          state = JSON.parse(result.content[0].text)
        } catch {
          return // Malformed JSON — silent
        }
        if (!state.error) {
          const scalar = (state.scalarCoherence as number) ?? 0
          set({
            connected: true,
            scalarCoherence: scalar,
            intentionality: (state.intentionality as number) ?? 0,
            breathEntrained: (state.breathEntrained as boolean) ?? false,
            consentLevel: (state.consentLevel as string) ?? 'SUSPENDED',
            bandAmplitudes: (state.bandAmplitudes as number[]) ?? [0, 0, 0, 0, 0],
            dominantBand: (state.dominantBand as string) ?? 'CORE',
            lastUpdate: Date.now(),
          })
          document.documentElement.style.setProperty(
            '--coherence',
            String(scalar)
          )

          // Track prompt in session
          const newPromptCount = get().promptCount + 1
          const newTokenEstimate = get().tokenEstimate + text.split(/\s+/).length * 2
          const sessionUpdates: Partial<CoherenceGloveState> = {
            promptCount: newPromptCount,
            tokenEstimate: newTokenEstimate,
          }

          // Check mid-session subjective prompt trigger
          const settings = JSON.parse(localStorage.getItem('coherenceGloveSettings') || '{}')
          const minPrompts = settings.midSessionMinPrompts ?? 3
          const minTokens = settings.midSessionMinTokens ?? 1000
          const enableMid = settings.enableMidSessionPrompt !== false

          if (enableMid && newPromptCount >= minPrompts && newTokenEstimate >= minTokens && !get().showSubjectivePrompt) {
            sessionUpdates.showSubjectivePrompt = true
            sessionUpdates.subjectivePromptSource = 'mid_session'
          }

          set(sessionUpdates)
        }
      }
    } catch {
      // Silent failure
    }
  },

  startPolling: () => {
    if (pollInterval) return
    // Initial poll + sensor status
    get().pollState()
    get().refreshSensors()
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

  refreshSensors: async () => {
    try {
      const result = await callTool({
        toolName: 'coherence_sensor_status',
        arguments: {},
      })
      if (result?.content?.[0]?.text) {
        let data: Record<string, unknown>
        try {
          data = JSON.parse(result.content[0].text)
        } catch {
          return
        }
        const available = data.available as SensorInfo[] | undefined
        if (available) {
          set({ sensors: available })
        }
      }
    } catch {
      // Silent — sensors are optional
    }
  },

  startSensor: async (name: string) => {
    set({ sensorLoading: true })
    try {
      await callTool({
        toolName: 'coherence_start_sensors',
        arguments: { sensors: [name] },
      })
      // Refresh sensor status after a short delay for subprocess to start
      setTimeout(() => get().refreshSensors(), 1500)
    } catch {
      console.error(`Failed to start sensor: ${name}`)
    } finally {
      set({ sensorLoading: false })
    }
  },

  stopSensor: async (name: string) => {
    set({ sensorLoading: true })
    try {
      await callTool({
        toolName: 'coherence_stop_sensors',
        arguments: { sensors: [name] },
      })
      await get().refreshSensors()
    } catch {
      console.error(`Failed to stop sensor: ${name}`)
    } finally {
      set({ sensorLoading: false })
    }
  },

  startSession: async () => {
    try {
      await callTool({ toolName: 'coherence_session_start', arguments: {} })
      set({ sessionActive: true, sessionPhase: 'dissolve', promptCount: 0, tokenEstimate: 0 })
    } catch { /* silent */ }
  },

  endSession: async () => {
    try {
      await callTool({ toolName: 'coherence_session_end', arguments: {} })
      set({ sessionActive: false, showSubjectivePrompt: true, subjectivePromptSource: 'end_session' })
    } catch { /* silent */ }
  },

  dismissSubjectivePrompt: () => {
    set({ showSubjectivePrompt: false })
  },
}))

export { useCoherenceGlove }
export type { SensorInfo }

import { create } from 'zustand'
import { callTool } from '@/services/mcp'

/**
 * Codex Tools — bridges QSE MCP server state to the frontend.
 *
 * Polls QSE state, exposes tool call helpers for validation,
 * LOKI analysis, tarot operators, and glyph checking.
 *
 * Silent when MCP server is offline.
 */

interface QSEModuleStatus {
  module: string
  passed: boolean
  score: number
  flags: { name: string; severity: string; message: string }[]
}

interface QSEVerdictResult {
  passed: boolean
  sigma_r: number
  verdict: string
  halted_at: string | null
  modules: QSEModuleStatus[]
}

interface LokiResult {
  disruptions: {
    category: string
    severity: string
    matches: string[]
    reframe: string
    count: number
  }[]
  severity: string
  reframe: string
  disruption_count: number
}

interface TarotResult {
  card: {
    id: number
    name: string
    codex_name: string
    glyph: string
    phase: string
    description: string
  }
  operator_prompt: string
  qse_role: string
  assessment: {
    status: string
    alignment: number
    message: string
  }
  recommendation: string
}

interface CodexToolsState {
  connected: boolean
  fieldPhase: string
  validationCount: number
  lastVerdict: QSEVerdictResult | null

  // Actions
  pollState: () => Promise<void>
  validateField: (args?: {
    emotionalTokens?: string[]
    identityAssertions?: string[]
    signalText?: string
  }) => Promise<QSEVerdictResult | null>
  runLoki: (text: string, context?: string) => Promise<LokiResult | null>
  runTarot: (arcanaId: number) => Promise<TarotResult | null>
  validateGlyphs: (glyphs: string[]) => Promise<{
    integrity_score: number
    broken_glyphs: string[]
  } | null>
  startPolling: () => void
  stopPolling: () => void
}

let pollInterval: ReturnType<typeof setInterval> | null = null

async function callQSE<T>(toolName: string, args: object = {}): Promise<T | null> {
  try {
    const response = await callTool({ toolName, arguments: args })
    if (response?.error) return null
    const text = response?.content?.[0]?.text
    if (!text) return null
    return JSON.parse(text) as T
  } catch {
    return null
  }
}

const useCodexTools = create<CodexToolsState>((set, get) => ({
  connected: false,
  fieldPhase: 'dormant',
  validationCount: 0,
  lastVerdict: null,

  pollState: async () => {
    const state = await callQSE<{
      field_phase: string
      validation_count: number
      last_verdict: QSEVerdictResult | null
    }>('qse_get_state')

    if (state) {
      set({
        connected: true,
        fieldPhase: state.field_phase,
        validationCount: state.validation_count,
        lastVerdict: state.last_verdict,
      })
    } else if (get().connected) {
      set({ connected: false })
    }
  },

  validateField: async (args) => {
    const result = await callQSE<QSEVerdictResult>('qse_validate_field', {
      emotional_tokens: args?.emotionalTokens,
      identity_assertions: args?.identityAssertions,
      signal_text: args?.signalText,
    })
    if (result) {
      set({ lastVerdict: result })
    }
    return result
  },

  runLoki: async (text, context) => {
    return callQSE<LokiResult>('qse_loki_operator', {
      signal_text: text,
      context,
    })
  },

  runTarot: async (arcanaId) => {
    return callQSE<TarotResult>('qse_tarot_operator', {
      arcana_id: arcanaId,
    })
  },

  validateGlyphs: async (glyphs) => {
    return callQSE<{ integrity_score: number; broken_glyphs: string[] }>(
      'qse_glyph_validate',
      { glyph_set: glyphs }
    )
  },

  startPolling: () => {
    if (pollInterval) return
    get().pollState()
    pollInterval = setInterval(() => get().pollState(), 10000)
  },

  stopPolling: () => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  },
}))

export default useCodexTools

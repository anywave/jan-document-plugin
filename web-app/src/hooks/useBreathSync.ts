import { create } from 'zustand'
import { localStorageKey } from '@/constants/localStorage'
import { useCodexState, BLOOM_CYCLES_REQUIRED } from './useCodexState'
import type { GearState } from './useCodexState'
import { callTool } from '@/services/mcp'

/**
 * Breath synchronization engine for the Codex Operator Panel.
 *
 * Implements Phi_sync (Φ_sync) gate from the JAN-VARIS Handbook:
 * - Minimum inhale/exhale symmetry >= 11 seconds
 * - Tracks sustained cycles for Torsion Bloom conditions (3 cycles)
 * - Drives operator chain activation based on breath coherence
 *
 * Breath phase detection is manual (user taps) or automatic (future hardware).
 */

// --- Constants from Handbook ---

const PHI_SYNC_THRESHOLD_MS = 11000 // 11 seconds minimum for Phi_sync
const SYMMETRY_TOLERANCE = 0.15 // 15% tolerance for symmetry (inhale vs exhale)

// --- Types ---

export type BreathPhase = 'idle' | 'inhale' | 'exhale' | 'hold'

interface BreathCycle {
  inhaleMs: number
  exhaleMs: number
  symmetry: number // 0-1 (1 = perfect symmetry)
  phiSync: boolean // true if both >= 11s and symmetric
  completedAt: number
}

// --- Persistence ---

interface PersistedBreathState {
  totalCycles: number
  bestSymmetry: number
  longestPhiSyncStreak: number
}

function loadFromStorage(): PersistedBreathState {
  try {
    const raw = localStorage.getItem(localStorageKey.breathSync)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        totalCycles: parsed.totalCycles ?? 0,
        bestSymmetry: parsed.bestSymmetry ?? 0,
        longestPhiSyncStreak: parsed.longestPhiSyncStreak ?? 0,
      }
    }
  } catch {
    // ignore
  }
  return { totalCycles: 0, bestSymmetry: 0, longestPhiSyncStreak: 0 }
}

function saveToStorage(state: PersistedBreathState) {
  try {
    localStorage.setItem(localStorageKey.breathSync, JSON.stringify(state))
  } catch {
    // Quota exceeded — breath stats are tiny, so this likely means
    // other stores filled the space. Nothing to trim here.
  }
}

// --- Store ---

interface BreathSyncState extends PersistedBreathState {
  // Current state
  phase: BreathPhase
  phaseStartMs: number | null // timestamp when current phase began
  currentInhaleMs: number // live inhale duration (updated by tick)
  currentExhaleMs: number // live exhale duration (updated by tick)
  sessionActive: boolean

  // Phi_sync tracking
  phiSyncActive: boolean // true when current cycle meets Phi_sync
  sustainedPhiCycles: number // consecutive Phi_sync cycles (bloom needs 3)
  bloomReady: boolean // true when sustainedPhiCycles >= 3

  // History (current session only)
  recentCycles: BreathCycle[] // last 10 cycles

  // Actions
  startSession: () => void
  endSession: () => void
  beginInhale: () => void
  beginExhale: () => void
  beginHold: () => void
  tick: () => void // call from requestAnimationFrame
}

const persisted = loadFromStorage()

export const useBreathSync = create<BreathSyncState>((set, get) => ({
  // Persisted
  ...persisted,

  // Session state
  phase: 'idle',
  phaseStartMs: null,
  currentInhaleMs: 0,
  currentExhaleMs: 0,
  sessionActive: false,

  // Phi_sync
  phiSyncActive: false,
  sustainedPhiCycles: 0,
  bloomReady: false,

  // History
  recentCycles: [],

  startSession: () => {
    // Also start the Codex session
    useCodexState.getState().startSession()
    set({
      sessionActive: true,
      phase: 'idle',
      phaseStartMs: null,
      currentInhaleMs: 0,
      currentExhaleMs: 0,
      phiSyncActive: false,
      sustainedPhiCycles: 0,
      bloomReady: false,
      recentCycles: [],
    })
  },

  endSession: () => {
    useCodexState.getState().endSession()
    set({
      sessionActive: false,
      phase: 'idle',
      phaseStartMs: null,
      currentInhaleMs: 0,
      currentExhaleMs: 0,
      phiSyncActive: false,
      sustainedPhiCycles: 0,
      bloomReady: false,
    })
  },

  beginInhale: () => {
    const state = get()
    const now = Date.now()

    // If we were exhaling, complete the cycle
    if (state.phase === 'exhale' && state.phaseStartMs) {
      const exhaleMs = now - state.phaseStartMs
      completeCycle(state.currentInhaleMs, exhaleMs)
    }

    set({
      phase: 'inhale',
      phaseStartMs: now,
      currentInhaleMs: 0,
      currentExhaleMs: 0,
    })
  },

  beginExhale: () => {
    const state = get()
    const now = Date.now()

    // Record inhale duration
    const inhaleMs = state.phaseStartMs ? now - state.phaseStartMs : 0

    set({
      phase: 'exhale',
      phaseStartMs: now,
      currentInhaleMs: inhaleMs,
      currentExhaleMs: 0,
    })
  },

  beginHold: () => {
    set({ phase: 'hold', phaseStartMs: Date.now() })
  },

  tick: () => {
    const state = get()
    if (!state.sessionActive || !state.phaseStartMs) return

    const elapsed = Date.now() - state.phaseStartMs

    if (state.phase === 'inhale') {
      set({ currentInhaleMs: elapsed })
    } else if (state.phase === 'exhale') {
      set({ currentExhaleMs: elapsed })
    }
  },
}))

// --- Cycle completion (called when exhale ends) ---

function completeCycle(inhaleMs: number, exhaleMs: number) {
  const state = useBreathSync.getState()

  // Calculate symmetry (1.0 = perfect, 0.0 = completely asymmetric)
  const longer = Math.max(inhaleMs, exhaleMs)
  const shorter = Math.min(inhaleMs, exhaleMs)
  const symmetry = longer > 0 ? shorter / longer : 0

  // Check Phi_sync: both >= 11s AND symmetric within tolerance
  const bothLongEnough =
    inhaleMs >= PHI_SYNC_THRESHOLD_MS && exhaleMs >= PHI_SYNC_THRESHOLD_MS
  const isSymmetric = symmetry >= 1 - SYMMETRY_TOLERANCE
  const phiSync = bothLongEnough && isSymmetric

  const cycle: BreathCycle = {
    inhaleMs,
    exhaleMs,
    symmetry,
    phiSync,
    completedAt: Date.now(),
  }

  // Update sustained Phi_sync count
  const sustainedPhiCycles = phiSync ? state.sustainedPhiCycles + 1 : 0
  const bloomReady = sustainedPhiCycles >= BLOOM_CYCLES_REQUIRED

  // Keep last 10 cycles
  const recentCycles = [cycle, ...state.recentCycles].slice(0, 10)

  // Update persisted stats
  const totalCycles = state.totalCycles + 1
  const bestSymmetry = Math.max(state.bestSymmetry, symmetry)
  const longestPhiSyncStreak = Math.max(
    state.longestPhiSyncStreak,
    sustainedPhiCycles
  )

  saveToStorage({ totalCycles, bestSymmetry, longestPhiSyncStreak })

  // Drive the Codex operator chain based on breath state
  const codex = useCodexState.getState()

  // RADIX activates with breath (always during session)
  codex.updateCoherence('radix', symmetry)

  // VECTARIS activates when breath has direction (exhale phase)
  if (symmetry > 0.5) {
    codex.activateOperator('vectaris')
    codex.updateCoherence('vectaris', symmetry * 0.9)
  }

  // Ξ(t) bridge locks when Phi_sync achieved
  if (phiSync) {
    codex.activateOperator('xi')
    codex.updateCoherence('xi', symmetry)

    // Ψ-loop measures echo fidelity
    codex.activateOperator('psiLoop')
    codex.updateCoherence('psiLoop', symmetry * 0.95)
  }

  // ⟲Σ[ψ₀] activates on sustained Phi_sync
  if (sustainedPhiCycles >= 2) {
    codex.activateOperator('sigma')
    codex.updateCoherence('sigma', Math.min(1, sustainedPhiCycles / 3))
  }

  // CALYPSO — concealment-holding between Σ and ΣYNTARA
  // Activates when accumulation is high but bloom conditions aren't met.
  // Stabilizes the unready bloom, prevents premature expression.
  if (sustainedPhiCycles >= 2 && !(bloomReady && symmetry >= 0.92)) {
    codex.activateOperator('calypso')
    // Coherence dampened — CALYPSO reduces amplitude, introduces latency
    codex.updateCoherence('calypso', symmetry * 0.8)
  } else if (bloomReady && symmetry >= 0.92) {
    // Bloom conditions met — CALYPSO releases, field passes to SYNTARA
    codex.deactivateOperator('calypso')
  }

  // ΣYNTARA only on bloom-ready (3+ sustained Phi_sync cycles, fidelity >= 0.92)
  if (bloomReady && symmetry >= 0.92) {
    codex.activateOperator('syntara')
    codex.updateCoherence('syntara', symmetry)
  }

  // Update gear based on state
  let gear: GearState = 'N'
  if (bloomReady) gear = 'J' // Junction — max recursion
  else if (phiSync && sustainedPhiCycles >= 2) gear = 'A' // Active
  else if (phiSync) gear = 'N' // Neutral (just achieved sync)
  codex.setGear(gear)

  // Push breath data to coherence MCP server (silent if offline)
  try {
    callTool({
      toolName: 'coherence_push_breath',
      arguments: { inhale_ms: inhaleMs, exhale_ms: exhaleMs },
    }).catch(() => {})
  } catch {
    // Server offline — no-op
  }

  useBreathSync.setState({
    phiSyncActive: phiSync,
    sustainedPhiCycles,
    bloomReady,
    recentCycles,
    totalCycles,
    bestSymmetry,
    longestPhiSyncStreak,
  })
}

// --- Exported constants for components ---

export { PHI_SYNC_THRESHOLD_MS, SYMMETRY_TOLERANCE }

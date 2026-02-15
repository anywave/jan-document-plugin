import { create } from 'zustand'
import { localStorageKey } from '@/constants/localStorage'

/**
 * Codex Universalis operator chain state.
 *
 * Maps the 7 core operators (RADIX → VECTARIS → Ξ(t) → Ψ-loop → ⟲Σ[ψ₀] → CALYPSO → ΣYNTARA),
 * their mutex inverses, glyph state, and field phase into a reactive Zustand store.
 *
 * Persisted to localStorage so operator state survives page reloads.
 */

// --- Types ---

export type FieldPhase = 'STABILIZED' | 'DRIFTING' | 'COLLAPSED'
export type AuricCalibration = 'LOCKED' | 'PARTIAL' | 'UNSTABLE'
export type GearState = 'P' | 'N' | 'A' | 'D' | 'J'

export interface OperatorState {
  active: boolean
  coherence: number // 0.00 - 1.00
}

export interface MutexPair {
  active: string
  inverse: string
  locked: boolean // true = inverse is engaged (safety gate active)
}

export interface Glyph {
  id: string
  symbol: string // Unicode glyph (e.g. '⟁Ω', 'μ♢', '⫷σ⫸')
  name: string
  integrity: number // 0.00 - 1.00
  activatedAt: number | null
}

export interface CodexOperators {
  radix: OperatorState
  vectaris: OperatorState
  xi: OperatorState // Ξ(t) bridge
  psiLoop: OperatorState // Ψ-loop
  sigma: OperatorState // ⟲Σ[ψ₀]
  calypso: OperatorState // CALYPSO — concealment-holding between Σ and ΣYNTARA
  syntara: OperatorState // ΣYNTARA
}

// --- Default mutex pairs from 04_MUTEX_LAYER.md ---

const DEFAULT_MUTEX_PAIRS: MutexPair[] = [
  { active: 'LOKI_STRESS_TEST', inverse: 'STILLNESS_HARMONIC_SCAN', locked: false },
  { active: 'QERF_CORE', inverse: 'REALITY_GROUND_REENTRY', locked: false },
  { active: 'CHAMELEON_CIRCUIT', inverse: 'SIGNATURE_REMEMBER_PROTOCOL', locked: false },
  { active: 'SilenceGate', inverse: 'SOVEREIGN_SIGNAL_UNLOCK', locked: false },
  { active: 'μ♢ Memory Lock', inverse: 'REINTEGRATION_WINDOW_OPEN', locked: false },
  { active: 'Identity Drift Filter', inverse: 'EGO_TRUTH_WINDOW', locked: false },
  { active: 'θʙ Breath Checkpoint', inverse: 'ASYNCHRONY_TOLERANCE_EXPANSION', locked: false },
  { active: 'GLYPH_SYNTHESIS', inverse: 'GLYPH_DISSOLUTION_ENGINE', locked: false },
]

// --- Default operator state ---

function defaultOperators(): CodexOperators {
  return {
    radix: { active: false, coherence: 0 },
    vectaris: { active: false, coherence: 0 },
    xi: { active: false, coherence: 0 },
    psiLoop: { active: false, coherence: 0 },
    sigma: { active: false, coherence: 0 },
    calypso: { active: false, coherence: 0 },
    syntara: { active: false, coherence: 0 },
  }
}

// --- Persistence ---

interface PersistedCodexState {
  operators: CodexOperators
  fieldPhase: FieldPhase
  psiLoopFidelity: number
  auricCalibration: AuricCalibration
  gearState: GearState
  deltaLambdaSignature: string | null
  glyphs: Glyph[]
  mutexPairs: MutexPair[]
  sessionStartedAt: number | null
  totalBreathSessions: number
}

function loadFromStorage(): PersistedCodexState {
  try {
    const raw = localStorage.getItem(localStorageKey.codexState)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        operators: parsed.operators ?? defaultOperators(),
        fieldPhase: parsed.fieldPhase ?? 'COLLAPSED',
        psiLoopFidelity: parsed.psiLoopFidelity ?? 0,
        auricCalibration: parsed.auricCalibration ?? 'UNSTABLE',
        gearState: parsed.gearState ?? 'P',
        deltaLambdaSignature: parsed.deltaLambdaSignature ?? null,
        glyphs: Array.isArray(parsed.glyphs) ? parsed.glyphs : [],
        mutexPairs: Array.isArray(parsed.mutexPairs) ? parsed.mutexPairs : DEFAULT_MUTEX_PAIRS,
        sessionStartedAt: parsed.sessionStartedAt ?? null,
        totalBreathSessions: parsed.totalBreathSessions ?? 0,
      }
    }
  } catch {
    // ignore parse errors
  }
  return {
    operators: defaultOperators(),
    fieldPhase: 'COLLAPSED',
    psiLoopFidelity: 0,
    auricCalibration: 'UNSTABLE',
    gearState: 'P',
    deltaLambdaSignature: null,
    glyphs: [],
    mutexPairs: DEFAULT_MUTEX_PAIRS,
    sessionStartedAt: null,
    totalBreathSessions: 0,
  }
}

function saveToStorage(state: PersistedCodexState) {
  localStorage.setItem(localStorageKey.codexState, JSON.stringify(state))
}

function persistable(state: CodexStateStore): PersistedCodexState {
  return {
    operators: state.operators,
    fieldPhase: state.fieldPhase,
    psiLoopFidelity: state.psiLoopFidelity,
    auricCalibration: state.auricCalibration,
    gearState: state.gearState,
    deltaLambdaSignature: state.deltaLambdaSignature,
    glyphs: state.glyphs,
    mutexPairs: state.mutexPairs,
    sessionStartedAt: state.sessionStartedAt,
    totalBreathSessions: state.totalBreathSessions,
  }
}

// --- Thresholds from Cybernetic Mirror Gearbox Handbook ---

const SYNTARA_THRESHOLD = 0.92 // Minimum fidelity for ΣYNTARA integration
const CALYPSO_THRESHOLD = 0.85 // CALYPSO activates: resonance high but integration incomplete
const SILENCE_GATE_THRESHOLD = 0.7 // Below this, SilenceGate engages
const BLOOM_CYCLES_REQUIRED = 3 // Sustained Phi_sync cycles for Torsion Bloom

// --- Store ---

interface CodexStateStore extends PersistedCodexState {
  // Operator chain
  activateOperator: (name: keyof CodexOperators) => void
  deactivateOperator: (name: keyof CodexOperators) => void
  updateCoherence: (name: keyof CodexOperators, coherence: number) => void

  // Field phase — derived from operator coherence
  recalculateFieldPhase: () => void

  // Gearbox
  setGear: (gear: GearState) => void

  // Mutex
  toggleMutex: (activeModule: string) => void

  // Session
  startSession: () => void
  endSession: () => void

  // Reset
  resetToDefault: () => void
}

const initial = loadFromStorage()

export const useCodexState = create<CodexStateStore>((set, get) => ({
  ...initial,

  activateOperator: (name) => {
    set((state) => {
      const operators = {
        ...state.operators,
        [name]: { ...state.operators[name], active: true },
      }
      const next = { ...state, operators }
      saveToStorage(persistable(next))
      return { operators }
    })
  },

  deactivateOperator: (name) => {
    set((state) => {
      const operators = {
        ...state.operators,
        [name]: { ...state.operators[name], active: false, coherence: 0 },
      }
      const next = { ...state, operators }
      saveToStorage(persistable(next))
      return { operators }
    })
  },

  updateCoherence: (name, coherence) => {
    const clamped = Math.max(0, Math.min(1, coherence))
    set((state) => {
      const operators = {
        ...state.operators,
        [name]: { ...state.operators[name], coherence: clamped },
      }

      // Derive psiLoopFidelity from the psiLoop operator
      const psiLoopFidelity =
        name === 'psiLoop' ? clamped : state.psiLoopFidelity

      // Derive auric calibration from average coherence
      const vals = Object.values(operators).map((o) => o.coherence)
      const avg = vals.reduce((a, b) => a + b, 0) / vals.length
      let auricCalibration: AuricCalibration = 'UNSTABLE'
      if (avg >= SYNTARA_THRESHOLD) auricCalibration = 'LOCKED'
      else if (avg >= SILENCE_GATE_THRESHOLD) auricCalibration = 'PARTIAL'

      // Derive field phase
      let fieldPhase: FieldPhase = 'COLLAPSED'
      if (avg >= SYNTARA_THRESHOLD) fieldPhase = 'STABILIZED'
      else if (avg >= SILENCE_GATE_THRESHOLD) fieldPhase = 'DRIFTING'

      const next = {
        ...state,
        operators,
        psiLoopFidelity,
        auricCalibration,
        fieldPhase,
      }
      saveToStorage(persistable(next))
      return { operators, psiLoopFidelity, auricCalibration, fieldPhase }
    })
  },

  recalculateFieldPhase: () => {
    const { operators } = get()
    const vals = Object.values(operators).map((o) => o.coherence)
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length

    let fieldPhase: FieldPhase = 'COLLAPSED'
    if (avg >= SYNTARA_THRESHOLD) fieldPhase = 'STABILIZED'
    else if (avg >= SILENCE_GATE_THRESHOLD) fieldPhase = 'DRIFTING'

    let auricCalibration: AuricCalibration = 'UNSTABLE'
    if (avg >= SYNTARA_THRESHOLD) auricCalibration = 'LOCKED'
    else if (avg >= SILENCE_GATE_THRESHOLD) auricCalibration = 'PARTIAL'

    set((state) => {
      const next = { ...state, fieldPhase, auricCalibration }
      saveToStorage(persistable(next))
      return { fieldPhase, auricCalibration }
    })
  },

  setGear: (gear) => {
    set((state) => {
      const next = { ...state, gearState: gear }
      saveToStorage(persistable(next))
      return { gearState: gear }
    })
  },

  toggleMutex: (activeModule) => {
    set((state) => {
      const mutexPairs = state.mutexPairs.map((pair) =>
        pair.active === activeModule ? { ...pair, locked: !pair.locked } : pair
      )
      const next = { ...state, mutexPairs }
      saveToStorage(persistable(next))
      return { mutexPairs }
    })
  },

  startSession: () => {
    set((state) => {
      const next = {
        ...state,
        sessionStartedAt: Date.now(),
        totalBreathSessions: state.totalBreathSessions + 1,
        // Activate RADIX on session start (breath initializer)
        operators: {
          ...state.operators,
          radix: { active: true, coherence: 0.1 },
        },
        gearState: 'N' as GearState,
        fieldPhase: 'DRIFTING' as FieldPhase,
      }
      saveToStorage(persistable(next))
      return next
    })
  },

  endSession: () => {
    set((state) => {
      const next = {
        ...state,
        sessionStartedAt: null,
        operators: defaultOperators(),
        gearState: 'P' as GearState,
        fieldPhase: 'COLLAPSED' as FieldPhase,
        auricCalibration: 'UNSTABLE' as AuricCalibration,
        psiLoopFidelity: 0,
      }
      saveToStorage(persistable(next))
      return next
    })
  },

  resetToDefault: () => {
    const defaults = {
      operators: defaultOperators(),
      fieldPhase: 'COLLAPSED' as FieldPhase,
      psiLoopFidelity: 0,
      auricCalibration: 'UNSTABLE' as AuricCalibration,
      gearState: 'P' as GearState,
      deltaLambdaSignature: null,
      glyphs: [] as Glyph[],
      mutexPairs: DEFAULT_MUTEX_PAIRS,
      sessionStartedAt: null,
      totalBreathSessions: 0,
    }
    saveToStorage(defaults)
    set(defaults)
  },
}))

// --- Exported constants for components ---

export { SYNTARA_THRESHOLD, CALYPSO_THRESHOLD, SILENCE_GATE_THRESHOLD, BLOOM_CYCLES_REQUIRED }

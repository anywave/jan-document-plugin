/**
 * MOBIUS Performance Mode
 *
 * System-level optimizations for maximum inference speed.
 * Each operation has a risk level and is user-gated with warnings.
 *
 * Risk levels:
 *   SAFE     — no downside, purely beneficial
 *   LOW      — minor tradeoff, easily reversible
 *   MODERATE — meaningful tradeoff, fully reversible but affects quality/UX
 */

import { Command } from '@tauri-apps/plugin-shell'

// ─── Types ─────────────────────────────────────────────────────────────────

export type RiskLevel = 'safe' | 'low' | 'moderate'

export interface PerformanceSetting {
  id: string
  enabled: boolean
  risk: RiskLevel
  available: boolean
  reason?: string // Why unavailable
}

export interface PerformanceModeState {
  kvCacheQuant: PerformanceSetting
  cachePrompt: PerformanceSetting
  gpuClockLock: PerformanceSetting
  powerPlan: PerformanceSetting & { currentPlan?: string }
}

export interface GpuClockInfo {
  currentMhz: number
  maxMhz: number
  locked: boolean
}

const PERF_STATE_KEY = 'mobius_performance_mode'
const MODEL_SETTINGS_PREFIX = 'mobius_model_settings_'

// ─── Persistence ───────────────────────────────────────────────────────────

export function getPerformanceModeState(): PerformanceModeState | null {
  const raw = localStorage.getItem(PERF_STATE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as PerformanceModeState
  } catch {
    return null
  }
}

export function storePerformanceModeState(state: PerformanceModeState): void {
  localStorage.setItem(PERF_STATE_KEY, JSON.stringify(state))
}

// ─── KV Cache Quantization ─────────────────────────────────────────────────
// Risk: LOW — slightly reduces generation quality in exchange for VRAM savings.
// KV cache stores attention keys/values. Q8_0 for keys (minimal loss) and
// Q4_0 for values (more compression, slightly more loss) is the sweet spot.

export function applyKvCacheQuant(modelId: string, enable: boolean): void {
  const key = `${MODEL_SETTINGS_PREFIX}${modelId}`
  const raw = localStorage.getItem(key)
  const settings = raw ? JSON.parse(raw) : {}

  if (enable) {
    settings.cache_type_k = 'q8_0'
    settings.cache_type_v = 'q4_0'
  } else {
    delete settings.cache_type_k
    delete settings.cache_type_v
  }

  localStorage.setItem(key, JSON.stringify(settings))
}

// ─── Prompt Cache ──────────────────────────────────────────────────────────
// Risk: SAFE — reuses KV cache across turns in the same conversation.
// Dramatically reduces time-to-first-token for follow-up messages.

export function applyCachePrompt(modelId: string, enable: boolean): void {
  const key = `${MODEL_SETTINGS_PREFIX}${modelId}`
  const raw = localStorage.getItem(key)
  const settings = raw ? JSON.parse(raw) : {}

  settings.cache_prompt = enable

  localStorage.setItem(key, JSON.stringify(settings))
}

// ─── GPU Clock Lock ────────────────────────────────────────────────────────
// Risk: MODERATE — locks GPU to max boost clock. Prevents thermal throttling
// from dynamically downclocking, but increases power draw and fan noise.
// GPU temperature may rise. Fully reversible with unlock.

export async function getGpuClockInfo(): Promise<GpuClockInfo | null> {
  try {
    const cmd = Command.create('nvidia-smi', [
      '--query-gpu=clocks.current.graphics,clocks.max.graphics',
      '--format=csv,noheader,nounits',
    ])
    const output = await cmd.execute()
    if (output.code !== 0) return null

    const parts = output.stdout.trim().split(',').map((s) => parseInt(s.trim(), 10))
    if (parts.length < 2 || isNaN(parts[0]) || isNaN(parts[1])) return null

    return {
      currentMhz: parts[0],
      maxMhz: parts[1],
      locked: Math.abs(parts[0] - parts[1]) < 50, // Within 50 MHz = effectively locked
    }
  } catch {
    return null
  }
}

export async function lockGpuClock(): Promise<boolean> {
  try {
    // First get max clock
    const info = await getGpuClockInfo()
    if (!info) return false

    const cmd = Command.create('nvidia-smi', [
      '-lgc', `${info.maxMhz}`,
    ])
    const output = await cmd.execute()
    return output.code === 0
  } catch {
    return false
  }
}

export async function unlockGpuClock(): Promise<boolean> {
  try {
    const cmd = Command.create('nvidia-smi', ['-rgc'])
    const output = await cmd.execute()
    return output.code === 0
  } catch {
    return false
  }
}

// ─── Windows Power Plan ────────────────────────────────────────────────────
// Risk: SAFE — just reports current power plan. User can change in Windows.

export async function getCurrentPowerPlan(): Promise<string | null> {
  try {
    const cmd = Command.create('powercfg', ['/getactivescheme'])
    const output = await cmd.execute()
    if (output.code !== 0) return null

    // Output format: "Power Scheme GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (High performance)"
    const match = output.stdout.match(/\(([^)]+)\)/)
    return match ? match[1] : output.stdout.trim()
  } catch {
    return null
  }
}

// ─── Build Default State ───────────────────────────────────────────────────

export function buildDefaultPerformanceState(
  hasNvidiaGpu: boolean
): PerformanceModeState {
  return {
    kvCacheQuant: {
      id: 'kvCacheQuant',
      enabled: false,
      risk: 'low',
      available: true,
    },
    cachePrompt: {
      id: 'cachePrompt',
      enabled: false,
      risk: 'safe',
      available: true,
    },
    gpuClockLock: {
      id: 'gpuClockLock',
      enabled: false,
      risk: 'moderate',
      available: hasNvidiaGpu,
      reason: hasNvidiaGpu ? undefined : 'No NVIDIA GPU detected',
    },
    powerPlan: {
      id: 'powerPlan',
      enabled: false,
      risk: 'safe',
      available: true,
    },
  }
}

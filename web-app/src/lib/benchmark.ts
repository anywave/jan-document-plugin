import { ExtensionManager } from '@/lib/extension'
import { getActiveModels, stopModel } from '@/services/models'
import {
  optimizeAnyModel,
  buildHardwareProfile,
  type HardwareProfile,
  type ModelOptimization,
} from '@/lib/modelOptimizer'
import type { HardwareData } from '@/hooks/useHardware'

export interface BenchmarkResult {
  model: string
  tokensPerSecond: number
  timeToFirstToken: number // ms
  totalTime: number // ms
  tokenCount: number
}

export interface BenchmarkProgress {
  phase: 'starting' | 'generating' | 'done'
  tokenCount: number
  text: string
}

export interface OptimizedSettings {
  n_gpu_layers: number
  ctx_size: number
  threads: number
  batch_size: number
  flash_attn: boolean
}

export interface StoredBenchmarkProfile {
  result: BenchmarkResult
  optimizedSettings: OptimizedSettings
  appliedAt: number | null
  timestamp: number
}

const BENCHMARK_PROMPT =
  'Explain how a computer processor executes instructions, step by step.'

export async function getLoadedLlamacppModel(): Promise<string | null> {
  const models = await getActiveModels('llamacpp')
  return models && models.length > 0 ? models[0] : null
}

export async function runBenchmark(
  onProgress?: (progress: BenchmarkProgress) => void,
  abortController?: AbortController
): Promise<BenchmarkResult> {
  const modelId = await getLoadedLlamacppModel()
  if (!modelId) throw new Error('No model loaded')

  const engine = ExtensionManager.getInstance().getEngine('llamacpp')
  if (!engine) throw new Error('llamacpp engine not available')

  const controller = abortController ?? new AbortController()
  onProgress?.({ phase: 'starting', tokenCount: 0, text: '' })

  const startTime = performance.now()
  let firstTokenTime = 0
  let tokenCount = 0
  let text = ''

  const response = await engine.chat(
    {
      model: modelId,
      messages: [{ role: 'user', content: BENCHMARK_PROMPT }],
      stream: true,
      n_predict: 128,
      temperature: 0,
    },
    controller
  )

  if (Symbol.asyncIterator in response) {
    for await (const chunk of response) {
      if (controller.signal.aborted) break
      const delta = chunk.choices?.[0]?.delta?.content
      if (delta) {
        if (tokenCount === 0) firstTokenTime = performance.now()
        tokenCount++
        text += delta
        onProgress?.({ phase: 'generating', tokenCount, text })
      }
    }
  }

  const endTime = performance.now()
  const ttft = firstTokenTime > 0 ? firstTokenTime - startTime : 0
  const generationTime = firstTokenTime > 0 ? endTime - firstTokenTime : 0
  const tokensPerSecond =
    tokenCount > 0 && generationTime > 0
      ? (tokenCount / generationTime) * 1000
      : 0

  onProgress?.({ phase: 'done', tokenCount, text })

  return {
    model: modelId,
    tokensPerSecond: Math.round(tokensPerSecond * 10) / 10,
    timeToFirstToken: Math.round(ttft),
    totalTime: Math.round(endTime - startTime),
    tokenCount,
  }
}

// ─── Optimization + Persistence ────────────────────────────────────────────

const BENCHMARK_PROFILE_KEY = 'mobius_benchmark_result'
const MODEL_SETTINGS_PREFIX = 'mobius_model_settings_'

/**
 * Compute optimal settings for the given model using hardware profile.
 */
export function computeOptimizedSettings(
  modelId: string,
  hardwareData: HardwareData
): OptimizedSettings {
  const profile = buildHardwareProfile(hardwareData)
  const opt = optimizeAnyModel(modelId, profile)
  return {
    n_gpu_layers: opt.ngl,
    ctx_size: opt.ctxSize,
    threads: opt.threads,
    batch_size: opt.batchSize,
    flash_attn: opt.flashAttn,
  }
}

/**
 * Read current model settings from localStorage.
 */
export function getCurrentModelSettings(
  modelId: string
): OptimizedSettings | null {
  const raw = localStorage.getItem(`${MODEL_SETTINGS_PREFIX}${modelId}`)
  if (!raw) return null
  try {
    return JSON.parse(raw) as OptimizedSettings
  } catch {
    return null
  }
}

/**
 * Store benchmark profile (result + optimized settings) in localStorage.
 */
export function storeBenchmarkProfile(profile: StoredBenchmarkProfile): void {
  localStorage.setItem(BENCHMARK_PROFILE_KEY, JSON.stringify(profile))
}

/**
 * Read stored benchmark profile from localStorage.
 */
export function getStoredBenchmarkProfile(): StoredBenchmarkProfile | null {
  const raw = localStorage.getItem(BENCHMARK_PROFILE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredBenchmarkProfile
  } catch {
    return null
  }
}

/**
 * Apply optimized settings: write to localStorage, update provider store, stop model.
 */
export async function applyOptimizedSettings(
  modelId: string,
  settings: OptimizedSettings,
  updateProviderFn: (modelId: string, settings: OptimizedSettings) => void
): Promise<void> {
  // 1. Write to localStorage for llamacpp extension to pick up on next model load
  const key = `${MODEL_SETTINGS_PREFIX}${modelId}`
  localStorage.setItem(key, JSON.stringify(settings))

  // 2. Update Zustand provider store so Model Settings UI reflects changes
  updateProviderFn(modelId, settings)

  // 3. Stop model to force restart with new settings
  await stopModel(modelId)

  // 4. Update stored benchmark profile with appliedAt timestamp
  const stored = getStoredBenchmarkProfile()
  if (stored) {
    stored.appliedAt = Date.now()
    storeBenchmarkProfile(stored)
  }
}

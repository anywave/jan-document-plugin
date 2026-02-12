/**
 * MOBIUS Model Optimizer Hook
 * Runs once on first launch after setup: detects hardware, optimizes MOBIUS model settings,
 * stores results in localStorage, and shows a toast notification.
 */

import { useEffect } from 'react'
import { toast } from 'sonner'
import { getHardwareInfo } from '@/services/hardware'
import { localStorageKey } from '@/constants/localStorage'
import {
  buildHardwareProfile,
  optimizeModel,
  formatOptimizationSummary,
  type ModelOptimization,
} from '@/lib/modelOptimizer'

const MOBIUS_OPTIMIZATION_DONE_KEY = 'mobius_optimization_done'
const MOBIUS_MODEL_SETTINGS_PREFIX = 'mobius_model_settings_'

const MOBIUS_MODEL_IDS = [
  'jan-nano-128k-iQ4_XS',
  'qwen2.5-7b-instruct-q4_k_m',
]

/**
 * Store optimization result in localStorage keyed by model ID.
 * The llamacpp extension reads these as override defaults.
 */
function storeOptimization(opt: ModelOptimization): void {
  const key = `${MOBIUS_MODEL_SETTINGS_PREFIX}${opt.modelId}`
  const settings = {
    n_gpu_layers: opt.ngl,
    ctx_size: opt.ctxSize,
    threads: opt.threads,
    batch_size: opt.batchSize,
    flash_attn: opt.flashAttn,
  }
  localStorage.setItem(key, JSON.stringify(settings))
}

export function useModelOptimizer(): void {
  useEffect(() => {
    // Skip if already optimized
    if (localStorage.getItem(MOBIUS_OPTIMIZATION_DONE_KEY)) return

    // Don't run until setup wizard is complete
    const setupCompleted = localStorage.getItem(localStorageKey.setupCompleted)
    if (setupCompleted !== 'true') return

    const runOptimization = async () => {
      try {
        const systemInfo = await getHardwareInfo()
        const profile = buildHardwareProfile(systemInfo)

        const optimizations: ModelOptimization[] = MOBIUS_MODEL_IDS.map(
          (modelId) => optimizeModel(modelId, profile)
        )

        // Store each optimization
        optimizations.forEach(storeOptimization)

        // Show persistent toast with summary
        const summary = formatOptimizationSummary(optimizations, profile)
        toast.info(summary, {
          duration: 15000,
        })

        // Mark as done
        localStorage.setItem(MOBIUS_OPTIMIZATION_DONE_KEY, 'true')
      } catch (error) {
        console.warn('[MOBIUS] Auto-optimization failed:', error)
      }
    }

    runOptimization()
  }, [])
}

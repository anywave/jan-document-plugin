/**
 * MOBIUS Model Optimizer
 * Pure TypeScript module for auto-optimizing MOBIUS model settings based on hardware.
 */

import type { HardwareData } from '@/hooks/useHardware'

export interface HardwareProfile {
  gpuVramMiB: number
  gpuVendor: string
  cpuCores: number
  systemRamMiB: number
  hasAvx2: boolean
}

export interface ModelOptimization {
  modelId: string
  ngl: number
  ctxSize: number
  threads: number
  batchSize: number
  flashAttn: boolean
  tier: string
}

/**
 * Build a hardware profile from system info returned by Tauri's get_system_info.
 */
export function buildHardwareProfile(systemInfo: HardwareData): HardwareProfile {
  // Find the GPU with the most VRAM
  let gpuVramMiB = 0
  let gpuVendor = 'None'

  if (systemInfo.gpus && systemInfo.gpus.length > 0) {
    const bestGpu = systemInfo.gpus.reduce((best, gpu) =>
      gpu.total_memory > best.total_memory ? gpu : best
    )
    gpuVramMiB = bestGpu.total_memory // already in MiB from Tauri
    gpuVendor = bestGpu.vendor || 'Unknown'

    // Normalize vendor name
    const vendorLower = gpuVendor.toLowerCase()
    if (vendorLower.includes('nvidia')) gpuVendor = 'NVIDIA'
    else if (vendorLower.includes('amd') || vendorLower.includes('advanced micro'))
      gpuVendor = 'AMD'
    else if (vendorLower.includes('intel')) gpuVendor = 'Intel'
  }

  const cpuCores = systemInfo.cpu?.core_count || 4
  const systemRamMiB = systemInfo.total_memory || 0

  // Check for AVX2 support in CPU extensions
  const extensions = systemInfo.cpu?.extensions || []
  const instructions = systemInfo.cpu?.instructions || []
  const allFeatures = [...extensions, ...instructions].map((s) => s.toLowerCase())
  const hasAvx2 = allFeatures.some((ext) => ext.includes('avx2'))

  return {
    gpuVramMiB,
    gpuVendor,
    cpuCores,
    systemRamMiB,
    hasAvx2,
  }
}

/**
 * VRAM tier thresholds in MiB.
 */
const VRAM_TIERS = [
  { name: 'No GPU', min: 0, max: 0 },
  { name: 'Low', min: 1, max: 4096 },
  { name: 'Medium', min: 4096, max: 6144 },
  { name: 'High', min: 6144, max: 8192 },
  { name: 'Very High', min: 8192, max: Infinity },
] as const

function getVramTier(vramMiB: number): string {
  if (vramMiB === 0) return 'No GPU'
  for (const tier of VRAM_TIERS) {
    if (vramMiB >= tier.min && vramMiB < tier.max) return tier.name
  }
  return 'Very High'
}

/**
 * Calculate optimal thread count: 75% of physical cores, minimum 1.
 */
function calculateThreads(cpuCores: number): number {
  return Math.max(1, Math.floor(cpuCores * 0.75))
}

/**
 * Optimize settings for a specific MOBIUS model based on hardware profile.
 */
export function optimizeModel(
  modelId: string,
  profile: HardwareProfile
): ModelOptimization {
  const tier = getVramTier(profile.gpuVramMiB)
  const threads = calculateThreads(profile.cpuCores)
  const isJanNano = modelId.includes('jan-nano')
  const isQwen = modelId.includes('qwen')

  let ngl: number
  let ctxSize: number
  let batchSize: number
  let flashAttn: boolean

  switch (tier) {
    case 'No GPU':
      ngl = 0
      ctxSize = isQwen ? 2048 : 2048
      batchSize = 512
      flashAttn = false
      break
    case 'Low':
      ngl = isJanNano ? 20 : 0
      ctxSize = isQwen ? 2048 : 4096
      batchSize = 512
      flashAttn = false
      break
    case 'Medium':
      ngl = isJanNano ? 37 : 10
      ctxSize = isQwen ? 4096 : 8192
      batchSize = 1024
      flashAttn = true
      break
    case 'High':
      ngl = isJanNano ? 37 : 25
      ctxSize = isQwen ? 4096 : 16384
      batchSize = 2048
      flashAttn = true
      break
    case 'Very High':
    default:
      ngl = 37
      ctxSize = isQwen ? 4096 : 32768
      batchSize = 2048
      flashAttn = true
      break
  }

  return {
    modelId,
    ngl,
    ctxSize,
    threads,
    batchSize,
    flashAttn,
    tier,
  }
}

/**
 * Format a human-readable summary of optimizations for toast display.
 */
export function formatOptimizationSummary(
  optimizations: ModelOptimization[],
  profile: HardwareProfile
): string {
  const gpuLine =
    profile.gpuVendor !== 'None'
      ? `Detected: ${profile.gpuVendor} (${Math.round(profile.gpuVramMiB / 1024)}GB VRAM), ${profile.cpuCores} cores, ${Math.round(profile.systemRamMiB / 1024)}GB RAM`
      : `Detected: No GPU, ${profile.cpuCores} cores, ${Math.round(profile.systemRamMiB / 1024)}GB RAM`

  const modelLines = optimizations
    .map((opt) => {
      const name = opt.modelId.includes('jan-nano')
        ? 'jan-nano-128k'
        : 'Qwen 2.5 7B'
      const fa = opt.flashAttn ? 'ON' : 'OFF'
      return `${name}: ${opt.ngl} GPU layers, ${opt.ctxSize} ctx, flash attention ${fa}`
    })
    .join('\n')

  const tier = optimizations[0]?.tier || 'Unknown'
  const threads = optimizations[0]?.threads || 1

  return `MOBIUS Auto-Optimization Complete\n\n${gpuLine}\n\n${modelLines}\nThreads: ${threads} | Tier: ${tier}\n\nAdjust in Jan AI Settings > llamacpp if needed.`
}

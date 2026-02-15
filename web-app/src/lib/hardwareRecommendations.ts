/**
 * MOBIUS Hardware Recommendations Engine
 *
 * Analyzes detected hardware and produces concrete upgrade/optimization
 * recommendations with impact estimates for local AI inference.
 */

import type { HardwareData } from '@/hooks/useHardware'

// ─── Types ─────────────────────────────────────────────────────────────────

export type ImpactLevel = 'high' | 'medium' | 'low'
export type RiskLevel = 'none' | 'low' | 'moderate' | 'high'

export interface Recommendation {
  id: string
  category: 'cpu' | 'ram' | 'gpu' | 'external'
  impact: ImpactLevel
  risk: RiskLevel
}

export interface CpuAnalysis {
  name: string
  cores: number
  threadsForInference: number // 75% of cores
  hasAvx2: boolean
  overclockable: boolean
  overclockRisk: string
  bottleneck: string | null // What's limiting CPU performance
}

export interface RamAnalysis {
  currentGiB: number
  maxModelWithCpuOffload: string // e.g. "7B Q4" or "13B Q4"
  upgradeImpact: RamUpgrade[]
}

export interface RamUpgrade {
  targetGiB: number
  modelsUnlocked: string
  contextGain: string
  estimatedCost: string
}

export interface GpuAnalysis {
  name: string
  vramGiB: number
  maxModelFullGpu: string
  upgradeImpact: GpuUpgrade[]
}

export interface GpuUpgrade {
  name: string
  vramGiB: number
  modelsUnlocked: string
  speedMultiplier: string
  estimatedCost: string
  formFactor: string // 'internal' | 'eGPU' | 'cloud'
}

export interface ExternalAcceleration {
  id: string
  name: string
  description: string
  howItWorks: string
  requirements: string
  estimatedCost: string
}

export interface HardwareRecommendations {
  cpu: CpuAnalysis
  ram: RamAnalysis
  gpu: GpuAnalysis
  external: ExternalAcceleration[]
  topRecommendation: string // Single most impactful upgrade
}

// ─── CPU Analysis ──────────────────────────────────────────────────────────

const OVERCLOCKABLE_PATTERNS = [
  /\bK\b/i, // Intel K-series (i7-9750K, etc.)
  /\bKF\b/i, // Intel KF
  /\bKS\b/i, // Intel KS
  /\bX\b/i, // Intel X-series
  /Ryzen.*X\b/i, // AMD Ryzen X-series
  /Ryzen.*X3D/i, // AMD X3D
  /Black Edition/i, // AMD Black Edition
  /Threadripper/i, // AMD Threadripper
]

function analyzeCpu(data: HardwareData): CpuAnalysis {
  const name = data.cpu?.name || 'Unknown CPU'
  const cores = data.cpu?.core_count || 4
  const threadsForInference = Math.max(1, Math.floor(cores * 0.75))

  const extensions = data.cpu?.extensions || []
  const instructions = data.cpu?.instructions || []
  const allFeatures = [...extensions, ...instructions].map((s) => s.toLowerCase())
  const hasAvx2 = allFeatures.some((ext) => ext.includes('avx2'))

  const overclockable = OVERCLOCKABLE_PATTERNS.some((p) => p.test(name))

  let bottleneck: string | null = null
  if (cores < 4) bottleneck = 'lowCores'
  else if (!hasAvx2) bottleneck = 'noAvx2'

  return {
    name,
    cores,
    threadsForInference,
    hasAvx2,
    overclockable,
    overclockRisk: overclockable ? 'moderate' : 'high',
    bottleneck,
  }
}

// ─── RAM Analysis ──────────────────────────────────────────────────────────

// Approximate model sizes in RAM for CPU-offloaded inference (Q4_K_M quant)
const RAM_MODEL_THRESHOLDS = [
  { gib: 8, model: '3B Q4' },
  { gib: 16, model: '7B Q4' },
  { gib: 32, model: '13B Q4 or 7B Q8' },
  { gib: 64, model: '30B Q4 or 13B Q8' },
  { gib: 128, model: '70B Q4 or 30B Q8' },
]

function analyzeRam(data: HardwareData): RamAnalysis {
  const totalMiB = data.total_memory || 0
  const currentGiB = Math.round(totalMiB / 1024)

  // What can run now (leaving ~4GB for OS)
  const usableGiB = Math.max(0, currentGiB - 4)
  let maxModel = '1B-3B models only'
  for (const t of RAM_MODEL_THRESHOLDS) {
    if (usableGiB >= t.gib - 4) maxModel = t.model
  }

  // Compute upgrade paths
  const upgrades: RamUpgrade[] = []
  const standardSizes = [16, 32, 64]

  for (const target of standardSizes) {
    if (target <= currentGiB) continue
    const usable = target - 4
    let unlocked = ''
    for (const t of RAM_MODEL_THRESHOLDS) {
      if (usable >= t.gib - 4) unlocked = t.model
    }

    const contextGain =
      target >= 64 ? '32K+ tokens' :
      target >= 32 ? '16K tokens' :
      '8K tokens'

    const cost =
      target === 16 ? '$25-40' :
      target === 32 ? '$50-80' :
      '$100-160'

    upgrades.push({
      targetGiB: target,
      modelsUnlocked: unlocked,
      contextGain,
      estimatedCost: cost,
    })
  }

  return {
    currentGiB,
    maxModelWithCpuOffload: maxModel,
    upgradeImpact: upgrades,
  }
}

// ─── GPU Analysis ──────────────────────────────────────────────────────────

// Approximate model sizes for full GPU inference (Q4_K_M quant)
const VRAM_MODEL_THRESHOLDS = [
  { gib: 4, model: '3B Q4' },
  { gib: 6, model: '7B Q4 (partial)' },
  { gib: 8, model: '7B Q4 (full)' },
  { gib: 12, model: '13B Q4 (partial)' },
  { gib: 16, model: '13B Q4 (full)' },
  { gib: 24, model: '30B Q4 or 13B Q8' },
  { gib: 48, model: '70B Q4' },
]

const GPU_UPGRADES: GpuUpgrade[] = [
  {
    name: 'RTX 4060 Ti 16GB',
    vramGiB: 16,
    modelsUnlocked: '13B Q4 full GPU',
    speedMultiplier: '2-3x over RTX 2060',
    estimatedCost: '$350-450',
    formFactor: 'internal',
  },
  {
    name: 'RTX 4070 Ti Super',
    vramGiB: 16,
    modelsUnlocked: '13B Q4 full GPU, faster',
    speedMultiplier: '3-4x over RTX 2060',
    estimatedCost: '$700-800',
    formFactor: 'internal',
  },
  {
    name: 'RTX 3060 12GB (Budget)',
    vramGiB: 12,
    modelsUnlocked: '7B Q8 or 13B Q4 partial',
    speedMultiplier: '1.5-2x over RTX 2060',
    estimatedCost: '$200-280',
    formFactor: 'internal',
  },
  {
    name: 'eGPU Enclosure + RTX 4060',
    vramGiB: 8,
    modelsUnlocked: 'Second GPU for tensor split',
    speedMultiplier: '1.5-2x with load balancing',
    estimatedCost: '$400-600 total',
    formFactor: 'eGPU',
  },
]

function analyzeGpu(data: HardwareData): GpuAnalysis {
  const gpu = data.gpus?.[0]
  const name = gpu?.name || 'No GPU detected'
  const vramMiB = gpu?.total_memory || 0
  const vramGiB = Math.round(vramMiB / 1024)

  let maxModel = 'CPU-only inference'
  for (const t of VRAM_MODEL_THRESHOLDS) {
    if (vramGiB >= t.gib) maxModel = t.model
  }

  // Filter upgrades to only show meaningful ones
  const upgrades = GPU_UPGRADES.filter((u) => u.vramGiB > vramGiB)

  return {
    name,
    vramGiB,
    maxModelFullGpu: maxModel,
    upgradeImpact: upgrades,
  }
}

// ─── External Acceleration ─────────────────────────────────────────────────

function getExternalOptions(): ExternalAcceleration[] {
  return [
    {
      id: 'eGPU',
      name: 'eGPU Enclosure',
      description: 'Add a desktop GPU to any laptop via Thunderbolt. Acts as a second GPU for tensor splitting.',
      howItWorks: 'llama.cpp supports --tensor-split to distribute model layers across multiple GPUs. An eGPU adds a second device to split the load with.',
      requirements: 'Thunderbolt 3/4 port, eGPU enclosure ($150-200), compatible GPU',
      estimatedCost: '$350-600 total',
    },
    {
      id: 'networkInference',
      name: 'Network Inference Server',
      description: 'Run the AI model on a more powerful machine on your network. MOBIUS connects to it like a local model.',
      howItWorks: 'llama.cpp can run as an OpenAI-compatible HTTP server on any machine. MOBIUS connects to it as a remote provider. Your powerful desktop runs the model; your laptop is just the UI.',
      requirements: 'Second machine with GPU on same network, llama.cpp server',
      estimatedCost: 'Free if you have a second machine',
    },
    {
      id: 'cloudGpu',
      name: 'Cloud GPU (On-Demand)',
      description: 'Rent GPU compute by the hour for heavy models you can\'t run locally.',
      howItWorks: 'Services like Runpod, Vast.ai, or Lambda provide GPU instances with llama.cpp pre-installed. Connect MOBIUS to their API endpoint.',
      requirements: 'Internet connection, cloud GPU account',
      estimatedCost: '$0.20-0.80/hour for RTX 4090 class',
    },
    {
      id: 'loadBalancer',
      name: 'Multi-GPU Load Balancer',
      description: 'Distribute inference across multiple GPUs (local + external) for maximum throughput.',
      howItWorks: 'llama.cpp --tensor-split divides model layers proportionally across GPUs by VRAM. Example: 60% on RTX 4070 (12GB) + 40% on RTX 2060 (6GB). Each GPU processes its layers in parallel.',
      requirements: 'Multiple GPUs (internal, eGPU, or network). MOBIUS GPU toggle in Settings > Hardware.',
      estimatedCost: 'Depends on second GPU choice',
    },
  ]
}

// ─── Main Analysis ─────────────────────────────────────────────────────────

export function analyzeHardware(data: HardwareData): HardwareRecommendations {
  const cpu = analyzeCpu(data)
  const ram = analyzeRam(data)
  const gpu = analyzeGpu(data)
  const external = getExternalOptions()

  // Determine the single most impactful recommendation
  let topRecommendation: string
  if (gpu.vramGiB === 0) {
    topRecommendation = 'addGpu'
  } else if (gpu.vramGiB < 8 && ram.currentGiB < 32) {
    topRecommendation = 'upgradeRam'
  } else if (gpu.vramGiB < 12) {
    topRecommendation = 'upgradeGpu'
  } else if (ram.currentGiB < 32) {
    topRecommendation = 'upgradeRam'
  } else {
    topRecommendation = 'external'
  }

  return { cpu, ram, gpu, external, topRecommendation }
}

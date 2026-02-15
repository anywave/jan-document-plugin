import { createFileRoute } from '@tanstack/react-router'
import { route } from '@/constants/routes'
import SettingsMenu from '@/containers/SettingsMenu'
import HeaderPage from '@/containers/HeaderPage'
import { Card, CardItem } from '@/containers/Card'
import { Switch } from '@/components/ui/switch'
import { Progress } from '@/components/ui/progress'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { useHardware } from '@/hooks/useHardware'
import { useLlamacppDevices } from '@/hooks/useLlamacppDevices'
import { useEffect, useState, useCallback, useRef } from 'react'
import { IconDeviceDesktopAnalytics } from '@tabler/icons-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'
import {
  getPerformanceModeState,
  storePerformanceModeState,
  buildDefaultPerformanceState,
  applyKvCacheQuant,
  applyCachePrompt,
  getGpuClockInfo,
  lockGpuClock,
  unlockGpuClock,
  getCurrentPowerPlan,
  type PerformanceModeState,
  type RiskLevel,
} from '@/lib/performanceMode'
import {
  buildHardwareProfile,
  calibrateSystem,
  optimizeAnyModel,
  type CalibrationResult,
  type SystemTier,
} from '@/lib/modelOptimizer'
import { getHardwareInfo, getSystemUsage } from '@/services/hardware'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'
import { formatMegaBytes } from '@/lib/utils'
import { windowKey } from '@/constants/windows'
import { toNumber } from '@/utils/number'
import { useModelProvider } from '@/hooks/useModelProvider'
import { stopAllModels } from '@/services/models'
import { toast } from 'sonner'
import {
  runBenchmark,
  getLoadedLlamacppModel,
  computeOptimizedSettings,
  getCurrentModelSettings,
  storeBenchmarkProfile,
  getStoredBenchmarkProfile,
  applyOptimizedSettings,
  type BenchmarkResult,
  type BenchmarkProgress,
  type OptimizedSettings,
} from '@/lib/benchmark'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute(route.settings.hardware as any)({
  component: Hardware,
})

const TIER_BADGE_STYLES: Record<SystemTier, string> = {
  Entry: 'bg-zinc-500 text-white',
  Standard: 'bg-blue-500 text-white',
  Performance: 'bg-green-500 text-black',
  Ultra: 'bg-purple-500 text-white',
}

const RISK_BADGE_STYLES: Record<RiskLevel, string> = {
  safe: 'bg-green-500/15 text-green-400',
  low: 'bg-yellow-500/15 text-yellow-400',
  moderate: 'bg-orange-500/15 text-orange-400',
}

const RISK_LABELS: Record<RiskLevel, string> = {
  safe: 'riskSafe',
  low: 'riskLow',
  moderate: 'riskModerate',
}

const CAPABILITY_LABELS = [
  { key: 'avx2', label: 'AVX2', tipKey: 'tipAvx2' },
  { key: 'flashAttention', label: 'Flash Attn', tipKey: 'tipFlashAttn' },
  { key: 'largeContext', label: 'Large Context', tipKey: 'tipLargeContext' },
  { key: 'multiGpu', label: 'Multi-GPU', tipKey: 'tipMultiGpu' },
  { key: 'vulkan', label: 'Vulkan', tipKey: 'tipVulkan' },
] as const

function Hardware() {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(false)
  const {
    hardwareData,
    systemUsage,
    setHardwareData,
    updateSystemUsage,
    pollingPaused,
  } = useHardware()

  const { providers } = useModelProvider()
  const llamacpp = providers.find((p) => p.provider === 'llamacpp')

  // ─── Calibration state ──────────────────────────────────
  const [calibration, setCalibration] = useState<CalibrationResult | null>(null)

  // ─── Benchmark state ──────────────────────────────────
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null)
  const [benchmarkProgress, setBenchmarkProgress] =
    useState<BenchmarkProgress | null>(null)
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null)
  const [loadedModel, setLoadedModel] = useState<string | null>(null)
  const benchmarkAbort = useRef<AbortController | null>(null)

  // ─── Optimization state ──────────────────────────────────
  const [optimizedSettings, setOptimizedSettings] = useState<OptimizedSettings | null>(null)
  const [currentSettings, setCurrentSettings] = useState<OptimizedSettings | null>(null)
  const [optimizationApplied, setOptimizationApplied] = useState(false)

  // ─── Performance Mode state ──────────────────────────────
  const [perfState, setPerfState] = useState<PerformanceModeState | null>(null)
  const [gpuClockMhz, setGpuClockMhz] = useState<string | null>(null)
  const [powerPlan, setPowerPlan] = useState<string | null>(null)

  const hasVulkan = hardwareData.gpus?.some(
    (g) => g.vulkan_info && g.vulkan_info.api_version !== ''
  ) ?? false

  const handleCalibrate = useCallback(() => {
    const profile = buildHardwareProfile(hardwareData)
    const result = calibrateSystem(
      profile,
      hardwareData.gpus?.length || 0,
      hasVulkan
    )
    setCalibration(result)
  }, [hardwareData, hasVulkan])

  // ─── Detect loaded model for benchmark ─────────────────
  useEffect(() => {
    const check = async () => {
      const model = await getLoadedLlamacppModel()
      setLoadedModel(model)
    }
    check()
    const id = setInterval(check, 5000)
    return () => clearInterval(id)
  }, [])

  // ─── Load stored benchmark on mount ──────────────────────
  useEffect(() => {
    const stored = getStoredBenchmarkProfile()
    if (stored) {
      setBenchmark(stored.result)
      setOptimizedSettings(stored.optimizedSettings)
      setCurrentSettings(getCurrentModelSettings(stored.result.model))
      setOptimizationApplied(stored.appliedAt !== null)
    }
  }, [])

  // ─── Load performance mode state on mount ────────────────
  useEffect(() => {
    const hasNvidia = hardwareData.gpus?.some(
      (g) => g.vendor?.toLowerCase().includes('nvidia')
    ) ?? false
    const stored = getPerformanceModeState()
    const state = stored ?? buildDefaultPerformanceState(hasNvidia)
    // Update availability based on current hardware
    state.gpuClockLock.available = hasNvidia
    if (!hasNvidia) state.gpuClockLock.reason = 'No NVIDIA GPU detected'
    setPerfState(state)

    // Probe system state
    if (hasNvidia) {
      getGpuClockInfo().then((info) => {
        if (info) {
          setGpuClockMhz(`${info.currentMhz} / ${info.maxMhz} MHz`)
          if (stored) {
            state.gpuClockLock.enabled = info.locked
          }
        }
      }).catch(() => {})
    }
    getCurrentPowerPlan().then((plan) => {
      if (plan) setPowerPlan(plan)
    }).catch(() => {})
  }, [hardwareData.gpus])

  const handleBenchmark = useCallback(async () => {
    setBenchmarkError(null)
    setBenchmark(null)
    setOptimizedSettings(null)
    setOptimizationApplied(false)
    benchmarkAbort.current = new AbortController()
    try {
      const result = await runBenchmark(
        setBenchmarkProgress,
        benchmarkAbort.current
      )
      setBenchmark(result)

      // Compute optimization after benchmark completes
      const settings = computeOptimizedSettings(result.model, hardwareData)
      setOptimizedSettings(settings)
      setCurrentSettings(getCurrentModelSettings(result.model))
      storeBenchmarkProfile({
        result,
        optimizedSettings: settings,
        appliedAt: null,
        timestamp: Date.now(),
      })
    } catch (e) {
      if (benchmarkAbort.current?.signal.aborted) return
      setBenchmarkError(e instanceof Error ? e.message : 'Benchmark failed')
    } finally {
      setBenchmarkProgress(null)
      benchmarkAbort.current = null
    }
  }, [hardwareData])

  const handleCancelBenchmark = useCallback(() => {
    benchmarkAbort.current?.abort()
    benchmarkAbort.current = null
    setBenchmarkProgress(null)
  }, [])

  const handleApplyOptimized = useCallback(async () => {
    if (!benchmark || !optimizedSettings) return
    await applyOptimizedSettings(
      benchmark.model,
      optimizedSettings,
      (modelId, settings) => {
        // Update provider store so Model Settings UI shows new values
        const provider = providers.find((p) => p.provider === 'llamacpp')
        if (!provider) return
        const updatedModels = provider.models.map((model) => {
          if (model.id !== modelId) return model
          const updatedSettings = { ...model.settings }
          if (updatedSettings.ctx_len) {
            updatedSettings.ctx_len = {
              ...updatedSettings.ctx_len,
              controller_props: {
                ...updatedSettings.ctx_len.controller_props,
                value: settings.ctx_size,
              },
            }
          }
          if (updatedSettings.ngl) {
            updatedSettings.ngl = {
              ...updatedSettings.ngl,
              controller_props: {
                ...updatedSettings.ngl.controller_props,
                value: settings.n_gpu_layers,
              },
            }
          }
          return { ...model, settings: updatedSettings }
        })
        const { updateProvider } = useModelProvider.getState()
        updateProvider('llamacpp', { models: updatedModels })
      }
    )
    setOptimizationApplied(true)
    setCurrentSettings(optimizedSettings)
    toast.success(t('settings:hardware.modelWillRestart'))
  }, [benchmark, optimizedSettings, providers, t])

  const handleApplyCalibration = useCallback(async () => {
    if (!loadedModel || !calibration) return
    const settings = computeOptimizedSettings(loadedModel, hardwareData)
    await applyOptimizedSettings(
      loadedModel,
      settings,
      (modelId, s) => {
        const provider = providers.find((p) => p.provider === 'llamacpp')
        if (!provider) return
        const updatedModels = provider.models.map((model) => {
          if (model.id !== modelId) return model
          const updatedSettings = { ...model.settings }
          if (updatedSettings.ctx_len) {
            updatedSettings.ctx_len = {
              ...updatedSettings.ctx_len,
              controller_props: {
                ...updatedSettings.ctx_len.controller_props,
                value: s.ctx_size,
              },
            }
          }
          if (updatedSettings.ngl) {
            updatedSettings.ngl = {
              ...updatedSettings.ngl,
              controller_props: {
                ...updatedSettings.ngl.controller_props,
                value: s.n_gpu_layers,
              },
            }
          }
          return { ...model, settings: updatedSettings }
        })
        const { updateProvider } = useModelProvider.getState()
        updateProvider('llamacpp', { models: updatedModels })
      }
    )
    toast.success(t('settings:hardware.calibrationApplied'))
  }, [loadedModel, calibration, hardwareData, providers, t])

  const handlePerfToggle = useCallback(async (
    settingId: keyof PerformanceModeState,
    enable: boolean
  ) => {
    if (!perfState || !loadedModel) return
    const next = { ...perfState }

    switch (settingId) {
      case 'kvCacheQuant':
        applyKvCacheQuant(loadedModel, enable)
        next.kvCacheQuant = { ...next.kvCacheQuant, enabled: enable }
        break
      case 'cachePrompt':
        applyCachePrompt(loadedModel, enable)
        next.cachePrompt = { ...next.cachePrompt, enabled: enable }
        break
      case 'gpuClockLock': {
        const ok = enable ? await lockGpuClock() : await unlockGpuClock()
        if (!ok) return
        next.gpuClockLock = { ...next.gpuClockLock, enabled: enable }
        // Refresh clock info
        const info = await getGpuClockInfo()
        if (info) setGpuClockMhz(`${info.currentMhz} / ${info.maxMhz} MHz`)
        break
      }
      default:
        return
    }

    setPerfState(next)
    storePerformanceModeState(next)

    // KV cache and cache_prompt require model restart
    if (settingId === 'kvCacheQuant' || settingId === 'cachePrompt') {
      const { stopModel } = await import('@/services/models')
      await stopModel(loadedModel)
      toast.success(
        enable
          ? t('settings:hardware.perfApplied')
          : t('settings:hardware.perfRemoved')
      )
    }
  }, [perfState, loadedModel, t])

  // Llamacpp devices hook
  const llamacppDevicesResult = useLlamacppDevices()

  // Use default values on macOS since llamacpp devices are not relevant
  const {
    devices: llamacppDevices,
    loading: llamacppDevicesLoading,
    error: llamacppDevicesError,
    toggleDevice,
    fetchDevices,
  } = IS_MACOS
    ? {
        devices: [],
        loading: false,
        error: null,
        toggleDevice: () => {},
        fetchDevices: () => {},
      }
    : llamacppDevicesResult

  // Fetch llamacpp devices when component mounts
  useEffect(() => {
    fetchDevices()
  }, [fetchDevices])

  // Fetch initial hardware info and system usage
  useEffect(() => {
    setIsLoading(true)
    Promise.all([
      getHardwareInfo()
        .then((data) => {
          setHardwareData(data)
        })
        .catch((error) => {
          console.error('Failed to get hardware info:', error)
        }),
      getSystemUsage()
        .then((data) => {
          updateSystemUsage(data)
        })
        .catch((error) => {
          console.error('Failed to get initial system usage:', error)
        }),
    ]).finally(() => {
      setIsLoading(false)
    })
  }, [setHardwareData, updateSystemUsage])



  useEffect(() => {
    if (pollingPaused) return undefined
    const intervalId = setInterval(() => {
      getSystemUsage()
        .then((data) => {
          updateSystemUsage(data)
        })
        .catch((error) => {
          console.error('Failed to get system usage:', error)
        })
    }, 5000)

    return () => clearInterval(intervalId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollingPaused])

  const handleClickSystemMonitor = async () => {
    try {
      // Check if system monitor window already exists
      const existingWindow = await WebviewWindow.getByLabel(
        windowKey.systemMonitorWindow
      )

      if (existingWindow) {
        // If window exists, focus it
        await existingWindow.setFocus()
        // focused existing monitor window
      } else {
        // Create a new system monitor window
        const monitorWindow = new WebviewWindow(windowKey.systemMonitorWindow, {
          url: route.systemMonitor,
          title: 'System Monitor - Jan',
          width: 900,
          height: 600,
          resizable: true,
          center: true,
        })

        // Listen for window creation
        monitorWindow.once('tauri://created', () => {
          // window ready
        })

        // Listen for window errors
        monitorWindow.once('tauri://error', (e) => {
          console.error('Error creating system monitor window:', e)
        })
      }
    } catch (error) {
      console.error('Failed to open system monitor window:', error)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <HeaderPage>
        <div className="flex items-center gap-2 justify-between w-full pr-3">
          <h1 className="font-medium">{t('common:settings')}</h1>
          <div
            className="flex items-center gap-1 hover:bg-main-view-fg/8 px-1.5 py-0.5 rounded relative z-10 cursor-pointer"
            onClick={handleClickSystemMonitor}
          >
            <IconDeviceDesktopAnalytics className="text-main-view-fg/50 size-5" />
            <p>{t('settings:hardware.systemMonitor')}</p>
          </div>
        </div>
      </HeaderPage>
      <div className="flex h-full w-full">
        <SettingsMenu />
        <div className="p-4 w-full h-[calc(100%-32px)] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-main-view-fg/50">
                Loading hardware information...
              </div>
            </div>
          ) : (
            <div className="flex flex-col justify-between gap-4 gap-y-3 w-full">
              {/* System Calibration */}
              <Card title={t('settings:hardware.calibration')}>
                {!calibration ? (
                  <CardItem
                    title={t('settings:hardware.calibrationDesc')}
                    actions={
                      <Button onClick={handleCalibrate}>
                        {t('settings:hardware.runCalibration')}
                      </Button>
                    }
                  />
                ) : (
                  <div className="space-y-4">
                    {/* Tier badge + summary */}
                    <div className="flex items-center gap-3">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold cursor-help ${TIER_BADGE_STYLES[calibration.tier]}`}
                          >
                            {t(`settings:hardware.tier${calibration.tier}`)}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs normal-case">
                          <p>{t(`settings:hardware.tipTier${calibration.tier}`)}</p>
                        </TooltipContent>
                      </Tooltip>
                      <span className="text-main-view-fg/70 text-sm">
                        {calibration.summary}
                      </span>
                    </div>

                    {/* Recommendations */}
                    <div className="space-y-0">
                      <CardItem
                        title={t('settings:hardware.recommendedModelSize')}
                        actions={
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="text-main-view-fg/80 cursor-help border-b border-dashed border-main-view-fg/20">
                                {calibration.recommendations.modelSize}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t('settings:hardware.tipModelSize')}</p>
                            </TooltipContent>
                          </Tooltip>
                        }
                      />
                      <CardItem
                        title={t('settings:hardware.quantization')}
                        actions={
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="text-main-view-fg/80 cursor-help border-b border-dashed border-main-view-fg/20">
                                {calibration.recommendations.quantization}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t('settings:hardware.tipQuantization')}</p>
                            </TooltipContent>
                          </Tooltip>
                        }
                      />
                      <CardItem
                        title={t('settings:hardware.maxContextWindow')}
                        actions={
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="text-main-view-fg/80 cursor-help border-b border-dashed border-main-view-fg/20">
                                {calibration.recommendations.maxContextLabel}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t('settings:hardware.tipMaxContext')}</p>
                            </TooltipContent>
                          </Tooltip>
                        }
                      />
                      <CardItem
                        title={t('settings:hardware.gpuAcceleration')}
                        actions={
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="text-main-view-fg/80 cursor-help border-b border-dashed border-main-view-fg/20">
                                {calibration.recommendations.gpuAcceleration}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t('settings:hardware.tipGpuAcceleration')}</p>
                            </TooltipContent>
                          </Tooltip>
                        }
                      />
                    </div>

                    {/* Capability pills */}
                    <div>
                      <h2 className="text-xs font-medium text-main-view-fg/50 mb-2">
                        {t('settings:hardware.capabilities')}
                      </h2>
                      <div className="flex flex-wrap gap-1.5">
                        {CAPABILITY_LABELS.map(({ key, label, tipKey }) => (
                          <Tooltip key={key}>
                            <TooltipTrigger asChild>
                              <span
                                className={`px-2 py-0.5 rounded-full text-xs font-medium cursor-help ${
                                  calibration.capabilities[key as keyof CalibrationResult['capabilities']]
                                    ? 'bg-green-500/15 text-green-400'
                                    : 'bg-zinc-500/15 text-zinc-500'
                                }`}
                              >
                                {label}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t(`settings:hardware.${tipKey}`)}</p>
                            </TooltipContent>
                          </Tooltip>
                        ))}
                      </div>
                    </div>

                    {/* CUDA Status */}
                    {(() => {
                      const nvidiaGpu = hardwareData.gpus?.find(
                        (g) => g.vendor?.toLowerCase().includes('nvidia')
                      )
                      if (!nvidiaGpu) {
                        return (
                          <div className="space-y-0">
                            <CardItem
                              title={t('settings:hardware.cudaStatus')}
                              actions={
                                <span className="text-zinc-500 text-sm">
                                  {t('settings:hardware.cudaNotDetected')}
                                </span>
                              }
                            />
                          </div>
                        )
                      }
                      const cc = nvidiaGpu.nvidia_info?.compute_capability || ''
                      const ccNum = parseFloat(cc) || 0
                      const isCompatible = ccNum >= 5.0
                      const hasTensorCores = ccNum >= 7.0
                      return (
                        <div className="space-y-0">
                          <CardItem
                            title={
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="cursor-help">{t('settings:hardware.cudaStatus')}</span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs normal-case">
                                  <p>{t('settings:hardware.tipCudaStatus')}</p>
                                </TooltipContent>
                              </Tooltip>
                            }
                            actions={
                              <span className={`text-sm font-medium ${isCompatible ? 'text-green-400' : 'text-red-400'}`}>
                                {isCompatible ? t('settings:hardware.cudaCompatible') : t('settings:hardware.cudaIncompatible')}
                              </span>
                            }
                          />
                          <CardItem
                            title={t('settings:hardware.cudaDriver')}
                            actions={
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="text-main-view-fg/80 cursor-help border-b border-dashed border-main-view-fg/20">
                                    {nvidiaGpu.driver_version}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs normal-case">
                                  <p>{t('settings:hardware.tipCudaDriver')}</p>
                                </TooltipContent>
                              </Tooltip>
                            }
                          />
                          <CardItem
                            title={t('settings:hardware.cudaComputeCap')}
                            actions={
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="text-main-view-fg/80 cursor-help border-b border-dashed border-main-view-fg/20">
                                    {cc}{hasTensorCores ? ' (Tensor Cores)' : ''}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs normal-case">
                                  <p>{t('settings:hardware.tipComputeCap')}</p>
                                </TooltipContent>
                              </Tooltip>
                            }
                          />
                        </div>
                      )
                    })()}

                    {/* Re-calibrate + Apply buttons */}
                    <div className="pt-1 flex gap-2">
                      <Button onClick={handleCalibrate}>
                        {t('settings:hardware.runCalibration')}
                      </Button>
                      {loadedModel && (
                        <Button onClick={handleApplyCalibration}>
                          {t('settings:hardware.applyCalibration')}
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </Card>

              {/* Benchmark */}
              <Card title={t('settings:hardware.benchmark')}>
                {!loadedModel ? (
                  <CardItem
                    title={t('settings:hardware.loadModelFirst')}
                    actions={
                      <Button disabled>
                        {t('settings:hardware.runBenchmark')}
                      </Button>
                    }
                  />
                ) : benchmarkProgress ? (
                  <div className="space-y-3">
                    <CardItem
                      title={`${t('settings:hardware.benchmarkRunning')} ${benchmarkProgress.tokenCount} tokens`}
                      actions={
                        <Button onClick={handleCancelBenchmark}>
                          {t('settings:hardware.benchmarkCancel')}
                        </Button>
                      }
                    />
                    {benchmarkProgress.text && (
                      <p className="text-xs text-main-view-fg/40 line-clamp-3 px-3 pb-2">
                        {benchmarkProgress.text}
                      </p>
                    )}
                  </div>
                ) : benchmark ? (
                  <div className="space-y-0">
                    <CardItem
                      title={t('settings:hardware.tokensPerSecond')}
                      actions={
                        <span className="text-main-view-fg font-semibold">
                          {benchmark.tokensPerSecond} tok/s
                        </span>
                      }
                    />
                    <CardItem
                      title={t('settings:hardware.timeToFirstToken')}
                      actions={
                        <span className="text-main-view-fg/80">
                          {benchmark.timeToFirstToken} ms
                        </span>
                      }
                    />
                    <CardItem
                      title={t('settings:hardware.totalTime')}
                      actions={
                        <span className="text-main-view-fg/80">
                          {(benchmark.totalTime / 1000).toFixed(1)} s
                        </span>
                      }
                    />
                    <CardItem
                      title={t('settings:hardware.tokensGenerated')}
                      actions={
                        <span className="text-main-view-fg/80">
                          {benchmark.tokenCount}
                        </span>
                      }
                    />
                    <CardItem
                      title={t('settings:hardware.benchmarkModel')}
                      actions={
                        <span className="text-main-view-fg/80">
                          {benchmark.model}
                        </span>
                      }
                    />
                    <div className="pt-2 px-3 pb-2">
                      <Button onClick={handleBenchmark}>
                        {t('settings:hardware.runAgain')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <CardItem
                      title={`${t('settings:hardware.benchmarkWith')} ${loadedModel}`}
                      actions={
                        <Button onClick={handleBenchmark}>
                          {t('settings:hardware.runBenchmark')}
                        </Button>
                      }
                    />
                    {benchmarkError && (
                      <p className="text-xs text-destructive px-3 pb-2">
                        {benchmarkError}
                      </p>
                    )}
                  </div>
                )}
              </Card>

              {/* Optimization — shown when benchmark results + optimized settings exist */}
              {benchmark && optimizedSettings && (
                <Card title={t('settings:hardware.optimizeTitle')}>
                  {optimizationApplied ? (
                    <div className="space-y-2">
                      <CardItem
                        title={`${t('settings:hardware.optimizedActive')} — ${t('settings:hardware.benchmarkedAt')} ${benchmark.tokensPerSecond} tok/s`}
                        actions={
                          <Button onClick={handleBenchmark}>
                            {t('settings:hardware.reBenchmark')}
                          </Button>
                        }
                      />
                    </div>
                  ) : (() => {
                    // Compute diffs between current and optimized settings
                    const diffs: { label: string; current: string; optimized: string }[] = []
                    const cur = currentSettings
                    const opt = optimizedSettings
                    if (!cur || cur.n_gpu_layers !== opt.n_gpu_layers)
                      diffs.push({ label: t('settings:hardware.gpuLayers'), current: cur ? String(cur.n_gpu_layers) : '—', optimized: String(opt.n_gpu_layers) })
                    if (!cur || cur.ctx_size !== opt.ctx_size)
                      diffs.push({ label: t('settings:hardware.contextSize'), current: cur ? String(cur.ctx_size) : '—', optimized: String(opt.ctx_size) })
                    if (!cur || cur.flash_attn !== opt.flash_attn)
                      diffs.push({ label: t('settings:hardware.flashAttention'), current: cur ? (cur.flash_attn ? 'ON' : 'OFF') : '—', optimized: opt.flash_attn ? 'ON' : 'OFF' })
                    if (!cur || cur.batch_size !== opt.batch_size)
                      diffs.push({ label: t('settings:hardware.batchSize'), current: cur ? String(cur.batch_size) : '—', optimized: String(opt.batch_size) })
                    if (!cur || cur.threads !== opt.threads)
                      diffs.push({ label: t('settings:hardware.cpuThreads'), current: cur ? String(cur.threads) : '—', optimized: String(opt.threads) })

                    if (diffs.length === 0) {
                      return (
                        <CardItem
                          title={t('settings:hardware.alreadyOptimal')}
                          actions={<></>}
                        />
                      )
                    }

                    return (
                      <div className="space-y-0">
                        <p className="text-sm text-main-view-fg/60 px-3 pt-2 pb-1">
                          {t('settings:hardware.optimizeDesc')}
                        </p>
                        {/* Header row */}
                        <div className="flex items-center justify-between px-3 py-1.5 text-xs text-main-view-fg/50 font-medium">
                          <span className="flex-1">{''}</span>
                          <span className="w-20 text-right">{t('settings:hardware.settingCurrent')}</span>
                          <span className="w-20 text-right">{t('settings:hardware.settingOptimized')}</span>
                        </div>
                        {diffs.map((diff) => (
                          <div key={diff.label} className="flex items-center justify-between px-3 py-1.5 text-sm border-t border-main-view-fg/5">
                            <span className="flex-1 text-main-view-fg/80">{diff.label}</span>
                            <span className="w-20 text-right text-main-view-fg/50">{diff.current}</span>
                            <span className="w-20 text-right text-green-400 font-medium">{diff.optimized}</span>
                          </div>
                        ))}
                        <div className="pt-2 px-3 pb-2">
                          <Button onClick={handleApplyOptimized}>
                            {t('settings:hardware.applyOptimized')}
                          </Button>
                        </div>
                      </div>
                    )
                  })()}
                </Card>
              )}

              {/* Performance Mode */}
              {perfState && (
                <Card title={t('settings:hardware.performanceMode')}>
                  <p className="text-xs text-main-view-fg/50 px-3 pb-3">
                    {t('settings:hardware.performanceModeDesc')}
                  </p>

                  {/* KV Cache Quantization */}
                  <div className="border-t border-main-view-fg/5">
                    <CardItem
                      title={
                        <div className="flex items-center gap-2">
                          <span>{t('settings:hardware.perfKvCache')}</span>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold cursor-help ${RISK_BADGE_STYLES[perfState.kvCacheQuant.risk]}`}>
                                {t(`settings:hardware.${RISK_LABELS[perfState.kvCacheQuant.risk]}`)}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t(`settings:hardware.${RISK_LABELS[perfState.kvCacheQuant.risk]}Desc`)}</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      }
                      description={t('settings:hardware.perfKvCacheDesc')}
                      actions={
                        <Switch
                          checked={perfState.kvCacheQuant.enabled}
                          disabled={!loadedModel}
                          onCheckedChange={(v) => handlePerfToggle('kvCacheQuant', v)}
                        />
                      }
                    />
                    {perfState.kvCacheQuant.enabled && (
                      <p className="text-[11px] text-yellow-400/70 px-3 pb-2">
                        {t('settings:hardware.perfKvCacheWarn')}
                      </p>
                    )}
                  </div>

                  {/* Prompt Cache */}
                  <div className="border-t border-main-view-fg/5">
                    <CardItem
                      title={
                        <div className="flex items-center gap-2">
                          <span>{t('settings:hardware.perfCachePrompt')}</span>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold cursor-help ${RISK_BADGE_STYLES[perfState.cachePrompt.risk]}`}>
                                {t(`settings:hardware.${RISK_LABELS[perfState.cachePrompt.risk]}`)}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t(`settings:hardware.${RISK_LABELS[perfState.cachePrompt.risk]}Desc`)}</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      }
                      description={t('settings:hardware.perfCachePromptDesc')}
                      actions={
                        <Switch
                          checked={perfState.cachePrompt.enabled}
                          disabled={!loadedModel}
                          onCheckedChange={(v) => handlePerfToggle('cachePrompt', v)}
                        />
                      }
                    />
                    {perfState.cachePrompt.enabled && (
                      <p className="text-[11px] text-green-400/70 px-3 pb-2">
                        {t('settings:hardware.perfCachePromptWarn')}
                      </p>
                    )}
                  </div>

                  {/* GPU Clock Lock */}
                  <div className="border-t border-main-view-fg/5">
                    <CardItem
                      title={
                        <div className="flex items-center gap-2">
                          <span>{t('settings:hardware.perfGpuClock')}</span>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold cursor-help ${RISK_BADGE_STYLES[perfState.gpuClockLock.risk]}`}>
                                {t(`settings:hardware.${RISK_LABELS[perfState.gpuClockLock.risk]}`)}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t(`settings:hardware.${RISK_LABELS[perfState.gpuClockLock.risk]}Desc`)}</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      }
                      description={t('settings:hardware.perfGpuClockDesc')}
                      actions={
                        perfState.gpuClockLock.available ? (
                          <Switch
                            checked={perfState.gpuClockLock.enabled}
                            onCheckedChange={(v) => handlePerfToggle('gpuClockLock', v)}
                          />
                        ) : (
                          <span className="text-xs text-zinc-500">
                            {perfState.gpuClockLock.reason || t('settings:hardware.perfUnavailable')}
                          </span>
                        )
                      }
                    />
                    {gpuClockMhz && (
                      <p className="text-[11px] text-main-view-fg/40 px-3 pb-1">
                        {t('settings:hardware.perfGpuClockCurrent')}: {gpuClockMhz}
                        {' — '}
                        {perfState.gpuClockLock.enabled
                          ? t('settings:hardware.perfGpuClockLocked')
                          : t('settings:hardware.perfGpuClockUnlocked')}
                      </p>
                    )}
                    {perfState.gpuClockLock.enabled && (
                      <p className="text-[11px] text-orange-400/70 px-3 pb-2">
                        {t('settings:hardware.perfGpuClockWarn')}
                      </p>
                    )}
                  </div>

                  {/* Windows Power Plan (read-only) */}
                  <div className="border-t border-main-view-fg/5">
                    <CardItem
                      title={
                        <div className="flex items-center gap-2">
                          <span>{t('settings:hardware.perfPowerPlan')}</span>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold cursor-help ${RISK_BADGE_STYLES.safe}`}>
                                {t('settings:hardware.riskSafe')}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs normal-case">
                              <p>{t('settings:hardware.perfPowerPlanWarn')}</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      }
                      description={t('settings:hardware.perfPowerPlanDesc')}
                      actions={
                        <span className={`text-sm font-medium ${
                          powerPlan?.toLowerCase().includes('high') || powerPlan?.toLowerCase().includes('ultimate')
                            ? 'text-green-400'
                            : 'text-yellow-400'
                        }`}>
                          {powerPlan || '...'}
                        </span>
                      }
                    />
                  </div>
                </Card>
              )}

              {/* OS Information */}
              <Card title={t('settings:hardware.os')}>
                <CardItem
                  title={t('settings:hardware.name')}
                  actions={
                    <span className="text-main-view-fg/80 capitalize">
                      {hardwareData.os_type}
                    </span>
                  }
                />
                <CardItem
                  title={t('settings:hardware.version')}
                  actions={
                    <span className="text-main-view-fg/80">
                      {hardwareData.os_name}
                    </span>
                  }
                />
              </Card>

              {/* CPU Information */}
              <Card title={t('settings:hardware.cpu')}>
                <CardItem
                  title={t('settings:hardware.model')}
                  actions={
                    <span className="text-main-view-fg/80">
                      {hardwareData.cpu?.name}
                    </span>
                  }
                />
                <CardItem
                  title={t('settings:hardware.architecture')}
                  actions={
                    <span className="text-main-view-fg/80">
                      {hardwareData.cpu?.arch}
                    </span>
                  }
                />
                <CardItem
                  title={t('settings:hardware.cores')}
                  actions={
                    <span className="text-main-view-fg/80">
                      {hardwareData.cpu?.core_count}
                    </span>
                  }
                />
                {hardwareData.cpu?.extensions?.join(', ').length > 0 && (
                  <CardItem
                    title={t('settings:hardware.instructions')}
                    column={hardwareData.cpu?.extensions.length > 6}
                    actions={
                      <span className="text-main-view-fg/80 break-words">
                        {hardwareData.cpu?.extensions?.join(', ')}
                      </span>
                    }
                  />
                )}
                <CardItem
                  title={t('settings:hardware.usage')}
                  actions={
                    <div className="flex items-center gap-2">
                      {systemUsage.cpu > 0 && (
                        <>
                          <Progress
                            value={systemUsage.cpu}
                            className="h-2 w-10"
                          />
                          <span className="text-main-view-fg/80">
                            {systemUsage.cpu?.toFixed(2)}%
                          </span>
                        </>
                      )}
                    </div>
                  }
                />
              </Card>

              {/* RAM Information */}
              <Card title={t('settings:hardware.memory')}>
                <CardItem
                  title={t('settings:hardware.totalRam')}
                  actions={
                    <span className="text-main-view-fg/80">
                      {formatMegaBytes(hardwareData.total_memory)}
                    </span>
                  }
                />
                <CardItem
                  title={t('settings:hardware.availableRam')}
                  actions={
                    <span className="text-main-view-fg/80">
                      {formatMegaBytes(
                        hardwareData.total_memory - systemUsage.used_memory
                      )}
                    </span>
                  }
                />
                <CardItem
                  title={t('settings:hardware.usage')}
                  actions={
                    <div className="flex items-center gap-2">
                      {hardwareData.total_memory > 0 && (
                        <>
                          <Progress
                            value={
                              toNumber(
                                systemUsage.used_memory /
                                  hardwareData.total_memory
                              ) * 100
                            }
                            className="h-2 w-10"
                          />
                          <span className="text-main-view-fg/80">
                            {(
                              toNumber(
                                systemUsage.used_memory /
                                  hardwareData.total_memory
                              ) * 100
                            ).toFixed(2)}
                            %
                          </span>
                        </>
                      )}
                    </div>
                  }
                />
              </Card>

              {/* Llamacpp Devices Information */}
              {!IS_MACOS && llamacpp && (
                <Card title="GPUs">
                  {llamacppDevicesLoading ? (
                    <CardItem title="Loading devices..." actions={<></>} />
                  ) : llamacppDevicesError ? (
                    <CardItem
                      title="Error loading devices"
                      actions={
                        <span className="text-destructive text-sm">
                          {llamacppDevicesError}
                        </span>
                      }
                    />
                  ) : llamacppDevices.length > 0 ? (
                    llamacppDevices.map((device, index) => (
                      <Card key={index}>
                        <CardItem
                          title={device.name}
                          actions={
                            <div className="flex items-center gap-4">
                              <div className="flex flex-col items-end gap-1">
                                <span className="text-main-view-fg/80 text-sm">
                                  ID: {device.id}
                                </span>
                                <span className="text-main-view-fg/80 text-sm">
                                  Memory: {formatMegaBytes(device.mem)} /{' '}
                                  {formatMegaBytes(device.free)} free
                                </span>
                              </div>
                              <Switch
                                checked={device.activated}
                                onCheckedChange={() => {
                                  toggleDevice(device.id)
                                  stopAllModels()
                                }}
                              />
                            </div>
                          }
                        />
                        <div className="mt-3">
                          <CardItem
                            title={t('settings:hardware.vram')}
                            actions={
                              <span className="text-main-view-fg/80">
                                {formatMegaBytes(device.free)}{' '}
                                {t('settings:hardware.freeOf')}{' '}
                                {formatMegaBytes(device.mem)}
                              </span>
                            }
                          />
                        </div>
                      </Card>
                    ))
                  ) : (
                    <CardItem title="No devices found" actions={<></>} />
                  )}
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

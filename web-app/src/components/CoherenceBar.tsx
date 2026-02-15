import { useCoherenceGlove } from '@/hooks/useCoherenceGlove'
import type { SensorInfo } from '@/hooks/useCoherenceGlove'
import { Switch } from '@/components/ui/switch'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { useEffect, useRef, useState } from 'react'

/**
 * CoherenceBar — 2px indicator at bottom of chat input.
 *
 * Color maps to phi-threshold consent levels:
 *   < 0.236 (phi^-3)    : transparent  (EMERGENCY)
 *   0.236-0.382 (phi^-2): dim violet   (SUSPENDED)
 *   0.382-0.618 (phi^-1): violet       (DIMINISHED)
 *   0.618-0.92  (phi^0) : gold         (FULL_CONSENT)
 *   >= 0.92 (SYNTARA)   : white        (STABILIZED)
 *
 * Click to expand sensor toggle panel.
 * Returns null when disconnected — no trace in the DOM.
 */

const PHI_NEG3 = 0.236
const PHI_NEG2 = 0.382
const PHI_NEG1 = 0.618
const SYNTARA = 0.92

function getBarColor(coherence: number): string {
  if (coherence >= SYNTARA) return 'rgba(255, 255, 255, 0.9)'
  if (coherence >= PHI_NEG1) return 'rgba(251, 191, 36, 0.8)'
  if (coherence >= PHI_NEG2) return 'rgba(168, 139, 250, 0.7)'
  if (coherence >= PHI_NEG3) return 'rgba(168, 139, 250, 0.35)'
  return 'transparent'
}

const CONSENT_KEYS: Record<string, string> = {
  STABILIZED: 'mobius:coherence.stabilized',
  FULL_CONSENT: 'mobius:coherence.fullConsent',
  DIMINISHED: 'mobius:coherence.diminished',
  SUSPENDED: 'mobius:coherence.suspended',
  EMERGENCY: 'mobius:coherence.emergency',
}

const SENSOR_LABEL_KEYS: Record<string, string> = {
  breath: 'mobius:coherence.breathMic',
  ppg: 'mobius:coherence.cameraPpg',
}

function SensorRow({
  sensor,
  loading,
  onToggle,
  t,
}: {
  sensor: SensorInfo
  loading: boolean
  onToggle: (name: string, running: boolean) => void
  t: (key: string) => string
}) {
  const label = SENSOR_LABEL_KEYS[sensor.name] ? t(SENSOR_LABEL_KEYS[sensor.name]) : sensor.name

  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-main-view-fg/70">{label}</span>
      {sensor.exists ? (
        <Switch
          checked={sensor.running}
          loading={loading}
          disabled={loading}
          onCheckedChange={() => onToggle(sensor.name, sensor.running)}
        />
      ) : (
        <span className="text-xs text-main-view-fg/30 italic">{t('mobius:coherence.notFound')}</span>
      )}
    </div>
  )
}

export function CoherenceBar() {
  const {
    connected,
    scalarCoherence,
    consentLevel,
    breathEntrained,
    sensors,
    sensorLoading,
    startPolling,
    stopPolling,
    startSensor,
    stopSensor,
  } = useCoherenceGlove()

  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  // Close panel on outside click
  useEffect(() => {
    if (!expanded) return
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setExpanded(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [expanded])

  if (!connected) return null

  const color = getBarColor(scalarCoherence)

  const handleToggle = (name: string, running: boolean) => {
    if (running) {
      stopSensor(name)
    } else {
      startSensor(name)
    }
  }

  return (
    <div ref={panelRef} className="relative w-full">
      {/* Expanded sensor panel */}
      {expanded && (
        <div
          className="absolute bottom-1 left-0 right-0 mx-2 rounded-lg border border-main-view-fg/10 bg-main-view p-3 shadow-lg"
          style={{ zIndex: 50 }}
        >
          {/* Coherence info row */}
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <div
                className="size-2 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs font-medium text-main-view-fg/90">
                {(scalarCoherence * 100).toFixed(0)}%
              </span>
              <span className="text-xs text-main-view-fg/50">
                {CONSENT_KEYS[consentLevel] ? t(CONSENT_KEYS[consentLevel]) : consentLevel}
              </span>
            </div>
            {breathEntrained && (
              <span className="text-xs text-main-view-fg/50">
                {t('mobius:coherence.breathEntrained')}
              </span>
            )}
          </div>

          {/* Sensor toggles */}
          {sensors.length > 0 && (
            <div className="border-t border-main-view-fg/10 mt-2 pt-2">
              <span className="text-[10px] uppercase tracking-wider text-main-view-fg/40 mb-1 block">
                {t('mobius:coherence.sensors')}
              </span>
              {sensors.map((s) => (
                <SensorRow
                  key={s.name}
                  sensor={s}
                  loading={sensorLoading}
                  onToggle={handleToggle}
                  t={t}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* The bar itself — clickable */}
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          height: 2,
          width: '100%',
          backgroundColor: color,
          transition: 'background-color 1s ease-in-out',
          borderRadius: 1,
          cursor: 'pointer',
        }}
        title={t('mobius:coherence.toggleSensors')}
      />
    </div>
  )
}

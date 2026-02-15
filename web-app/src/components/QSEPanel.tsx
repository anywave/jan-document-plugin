import { useEffect } from 'react'
import useCodexTools from '@/hooks/useCodexTools'
import { cn } from '@/lib/utils'

/**
 * QSE Panel — displays 7-module validation status.
 * Each module shows green (pass), amber (warning), or red (fail).
 */

const MODULE_LABELS: Record<string, string> = {
  breath_symmetry: 'Breath',
  emotional_tone: 'Emotion',
  identity_mirror: 'Identity',
  resonance: 'Resonance',
  amplification: 'Amplify',
  coercion: 'Coercion',
  integration: 'Integrate',
}

function statusColor(passed: boolean, score: number): string {
  if (passed && score >= 0.8) return 'bg-green-500'
  if (passed) return 'bg-amber-400'
  return 'bg-red-500'
}

function statusTextColor(passed: boolean, score: number): string {
  if (passed && score >= 0.8) return 'text-green-500'
  if (passed) return 'text-amber-400'
  return 'text-red-500'
}

export function QSEPanel() {
  const {
    connected,
    fieldPhase,
    lastVerdict,
    validationCount,
    startPolling,
    stopPolling,
    validateField,
  } = useCodexTools()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  if (!connected) {
    return (
      <div className="p-3 text-xs text-main-view-fg/30">
        QSE offline
      </div>
    )
  }

  const modules = lastVerdict?.modules ?? []

  return (
    <div className="p-3 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-main-view-fg/70">
            QSE
          </span>
          <span
            className={cn(
              'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
              lastVerdict?.passed
                ? 'bg-green-500/10 text-green-500'
                : 'bg-main-view-fg/5 text-main-view-fg/50'
            )}
          >
            {fieldPhase}
          </span>
        </div>
        {lastVerdict && (
          <span className="text-[10px] font-mono text-main-view-fg/40">
            Σᵣ {lastVerdict.sigma_r.toFixed(3)}
          </span>
        )}
      </div>

      {/* Module status grid */}
      {modules.length > 0 && (
        <div className="grid grid-cols-7 gap-1">
          {modules.map((m) => (
            <div
              key={m.module}
              className="flex flex-col items-center gap-1"
              title={`${m.module}: ${m.score.toFixed(2)} — ${m.passed ? 'PASS' : 'FAIL'}${
                m.flags.length ? '\n' + m.flags.map((f) => f.message).join('\n') : ''
              }`}
            >
              <div
                className={cn(
                  'size-2 rounded-full',
                  statusColor(m.passed, m.score)
                )}
              />
              <span className="text-[8px] text-main-view-fg/40 leading-none">
                {MODULE_LABELS[m.module] ?? m.module.slice(0, 6)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Verdict */}
      {lastVerdict && (
        <div
          className={cn(
            'text-[10px] font-medium text-center py-1 rounded',
            lastVerdict.passed
              ? 'bg-green-500/5 text-green-500/80'
              : 'bg-main-view-fg/[0.02] text-main-view-fg/40'
          )}
        >
          {lastVerdict.verdict}
        </div>
      )}

      {/* Run button */}
      <button
        onClick={() => validateField()}
        className="w-full text-[10px] py-1 rounded border border-main-view-fg/10
          hover:bg-main-view-fg/5 text-main-view-fg/50 transition-colors"
      >
        Run Validation ({validationCount})
      </button>
    </div>
  )
}

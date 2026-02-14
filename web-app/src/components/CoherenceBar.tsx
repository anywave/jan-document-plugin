import { useCoherenceGlove } from '@/hooks/useCoherenceGlove'
import { useEffect } from 'react'

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

export function CoherenceBar() {
  const { connected, scalarCoherence, startPolling, stopPolling } =
    useCoherenceGlove()

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [startPolling, stopPolling])

  if (!connected) return null

  const color = getBarColor(scalarCoherence)

  return (
    <div
      style={{
        height: 2,
        width: '100%',
        backgroundColor: color,
        transition: 'background-color 1s ease-in-out',
        borderRadius: 1,
      }}
    />
  )
}

import { useState } from 'react'
import useCodexTools from '@/hooks/useCodexTools'
import { cn } from '@/lib/utils'

/**
 * LOKI Sandbox — text input for phase disruption analysis.
 * Paste or type text, LOKI scans for cognitive distortion patterns
 * and offers reframe suggestions.
 */

const SEVERITY_COLORS: Record<string, string> = {
  none: 'text-green-500',
  low: 'text-blue-400',
  medium: 'text-amber-400',
  high: 'text-orange-500',
  critical: 'text-red-500',
}

export function LokiSandbox() {
  const { runLoki, connected } = useCodexTools()
  const [text, setText] = useState('')
  const [result, setResult] = useState<{
    disruptions: {
      category: string
      severity: string
      matches: string[]
      reframe: string
      count: number
    }[]
    severity: string
    reframe: string
    disruption_count: number
  } | null>(null)
  const [loading, setLoading] = useState(false)

  const handleAnalyze = async () => {
    if (!text.trim()) return
    setLoading(true)
    const res = await runLoki(text.trim())
    if (res) setResult(res)
    setLoading(false)
  }

  if (!connected) {
    return (
      <div className="p-3 text-xs text-main-view-fg/30">
        Codex Tools offline
      </div>
    )
  }

  return (
    <div className="p-3 space-y-3">
      <h3 className="text-xs font-medium text-main-view-fg/70">
        LOKI Disruption Scanner
      </h3>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste text to scan for cognitive disruption patterns..."
        className="w-full h-20 text-xs p-2 rounded border border-main-view-fg/10
          bg-transparent resize-none placeholder:text-main-view-fg/20
          focus:outline-none focus:border-main-view-fg/20"
      />

      <button
        onClick={handleAnalyze}
        disabled={loading || !text.trim()}
        className="w-full text-[10px] py-1.5 rounded border border-main-view-fg/10
          hover:bg-main-view-fg/5 text-main-view-fg/50 transition-colors
          disabled:opacity-30 disabled:cursor-not-allowed"
      >
        {loading ? 'Scanning...' : 'Run LOKI Analysis'}
      </button>

      {result && (
        <div className="space-y-2 border-t border-main-view-fg/5 pt-2">
          {/* Overall severity */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-main-view-fg/40">Severity</span>
            <span
              className={cn(
                'text-xs font-medium uppercase',
                SEVERITY_COLORS[result.severity] ?? 'text-main-view-fg/50'
              )}
            >
              {result.severity}
            </span>
          </div>

          {/* Disruptions */}
          {result.disruptions.length > 0 ? (
            <div className="space-y-2">
              {result.disruptions.map((d, i) => (
                <div
                  key={i}
                  className="rounded border border-main-view-fg/5 p-2 space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium text-main-view-fg/60">
                      {d.category.replace('_', ' ')}
                    </span>
                    <span
                      className={cn(
                        'text-[9px] uppercase',
                        SEVERITY_COLORS[d.severity] ?? ''
                      )}
                    >
                      {d.severity}
                    </span>
                  </div>
                  <p className="text-[10px] text-main-view-fg/40">
                    Matches: {d.matches.join(', ')}
                  </p>
                  <p className="text-[10px] text-main-view-fg/60 italic">
                    {d.reframe}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[10px] text-green-500/60 text-center py-2">
              No disruptions detected. The field is clear.
            </div>
          )}

          {/* Primary reframe */}
          {result.disruption_count > 0 && (
            <div className="bg-main-view-fg/[0.02] rounded p-2">
              <span className="text-[9px] text-main-view-fg/30 uppercase tracking-wide">
                Reframe
              </span>
              <p className="text-[11px] text-main-view-fg/70 mt-0.5 italic">
                {result.reframe}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import useCodexTools from '@/hooks/useCodexTools'
import { cn } from '@/lib/utils'

/**
 * Codex Tarot Operator — select a Major Arcana card and run its operator.
 */

const ARCANA_NAMES = [
  'The Fool', 'The Magician', 'High Priestess', 'The Empress',
  'The Emperor', 'Hierophant', 'The Lovers', 'The Chariot',
  'Strength', 'The Hermit', 'Wheel of Fortune', 'Justice',
  'Hanged Man', 'Death', 'Temperance', 'The Devil',
  'The Tower', 'The Star', 'The Moon', 'The Sun',
  'Judgement', 'The World',
]

export function TarotOperator() {
  const { runTarot, connected } = useCodexTools()
  const [selectedCard, setSelectedCard] = useState<number | null>(null)
  const [result, setResult] = useState<{
    card: { name: string; glyph: string; description: string; codex_name: string }
    assessment: { alignment: number; message: string }
    recommendation: string
    operator_prompt: string
  } | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRun = async (id: number) => {
    setSelectedCard(id)
    setLoading(true)
    const res = await runTarot(id)
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
        Codex Tarot
      </h3>

      {/* Card grid — compact 2-column */}
      <div className="grid grid-cols-2 gap-1 max-h-48 overflow-y-auto">
        {ARCANA_NAMES.map((name, i) => (
          <button
            key={i}
            onClick={() => handleRun(i)}
            className={cn(
              'text-[10px] py-1 px-2 rounded text-left truncate transition-colors',
              selectedCard === i
                ? 'bg-main-view-fg/10 text-main-view-fg/80'
                : 'hover:bg-main-view-fg/5 text-main-view-fg/50'
            )}
          >
            <span className="font-mono mr-1 text-main-view-fg/30">
              {String(i).padStart(2, '0')}
            </span>
            {name}
          </button>
        ))}
      </div>

      {/* Result */}
      {loading && (
        <div className="text-[10px] text-main-view-fg/40 text-center">
          Running operator...
        </div>
      )}
      {result && !loading && (
        <div className="space-y-2 border-t border-main-view-fg/5 pt-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">{result.card.glyph}</span>
            <div>
              <div className="text-xs font-medium">{result.card.name}</div>
              <div className="text-[10px] text-main-view-fg/40">
                {result.card.codex_name}
              </div>
            </div>
          </div>
          <p className="text-[11px] text-main-view-fg/60 italic">
            {result.card.description}
          </p>

          {/* Alignment bar */}
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 rounded-full bg-main-view-fg/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-green-500/60 transition-all duration-500"
                style={{ width: `${result.assessment.alignment * 100}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-main-view-fg/40">
              {(result.assessment.alignment * 100).toFixed(0)}%
            </span>
          </div>

          <p className="text-[10px] text-main-view-fg/50">
            {result.assessment.message}
          </p>
          <p className="text-[10px] text-main-view-fg/70 font-medium">
            {result.recommendation}
          </p>
        </div>
      )}
    </div>
  )
}

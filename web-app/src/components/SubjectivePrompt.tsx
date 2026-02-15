import { useState } from 'react'
import { callTool } from '@/services/mcp'

interface SubjectivePromptProps {
  source: 'mid_session' | 'end_session'
  onDismiss: () => void
}

export function SubjectivePrompt({ source, onDismiss }: SubjectivePromptProps) {
  const [score, setScore] = useState(5)
  const [submitting, setSubmitting] = useState(false)

  const label = source === 'mid_session'
    ? 'How coherent do you feel right now?'
    : 'How did that session feel overall?'

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await callTool({
        toolName: 'coherence_push_subjective',
        arguments: { score, source },
      })
    } catch {
      // Silent — non-critical
    } finally {
      setSubmitting(false)
      onDismiss()
    }
  }

  return (
    <div className="fixed bottom-16 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 border border-zinc-700 rounded-lg p-4 shadow-lg w-80">
      <p className="text-sm text-zinc-300 mb-3">{label}</p>
      <div className="flex items-center gap-3">
        <span className="text-xs text-zinc-500">0</span>
        <input
          type="range"
          min={0}
          max={10}
          step={1}
          value={score}
          onChange={(e) => setScore(Number(e.target.value))}
          className="flex-1 accent-violet-500"
        />
        <span className="text-xs text-zinc-500">10</span>
        <span className="text-sm font-mono text-violet-400 w-6 text-center">{score}</span>
      </div>
      <div className="flex justify-end gap-2 mt-3">
        <button
          onClick={onDismiss}
          className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1"
        >
          Skip
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1 rounded disabled:opacity-50"
        >
          {submitting ? '...' : 'Submit'}
        </button>
      </div>
    </div>
  )
}

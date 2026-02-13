import { X } from 'lucide-react'
import type { Annotation } from '@/hooks/useChatExcerpts'

interface AnnotationCardProps {
  annotation: Annotation
  onRemove: (id: string) => void
}

export function AnnotationCard({ annotation, onRemove }: AnnotationCardProps) {
  const date = new Date(annotation.createdAt)
  const timeStr = date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="relative w-48 p-2 bg-main-view-fg/5 border border-main-view-fg/10 rounded-md shadow-sm">
      {/* Connector line */}
      <div className="absolute top-4 -right-3 w-3 h-px bg-main-view-fg/20" />

      {/* Remove button */}
      <button
        onClick={() => onRemove(annotation.id)}
        className="absolute top-1 right-1 p-0.5 rounded hover:bg-main-view-fg/10 text-muted-fg"
      >
        <X className="h-3 w-3" />
      </button>

      {/* Summary text */}
      <p className="text-xs leading-relaxed text-main-view-fg pr-4">
        {annotation.summary}
      </p>

      {/* Timestamp */}
      <p className="text-[10px] text-muted-fg mt-1">{timeStr}</p>
    </div>
  )
}

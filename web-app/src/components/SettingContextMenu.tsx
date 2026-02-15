import { useEffect, useRef } from 'react'
import { IconWand, IconCopy, IconInfoCircle } from '@tabler/icons-react'
import { paramsSettings } from '@/lib/predefinedParams'

interface SettingContextMenuProps {
  settingKey: string
  currentValue: unknown
  optimalValue?: number | boolean
  position: { x: number; y: number }
  onClose: () => void
  onResetToOptimal: () => void
}

export function SettingContextMenu({
  settingKey,
  currentValue,
  optimalValue,
  position,
  onClose,
  onResetToOptimal,
}: SettingContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)
  const param = paramsSettings[settingKey]

  // Close on click outside or Escape
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])

  // Clamp position to viewport
  const style = {
    top: Math.min(position.y, window.innerHeight - 320),
    left: Math.min(position.x, window.innerWidth - 300),
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(String(currentValue ?? ''))
    onClose()
  }

  return (
    <div
      ref={menuRef}
      className="fixed z-50 w-72 rounded-lg border border-main-view-fg/10 bg-main-view-bg
        shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-100"
      style={style}
    >
      {/* Header: Setting name */}
      <div className="px-3 py-2 border-b border-main-view-fg/5 bg-main-view-fg/[0.02]">
        <h4 className="font-medium text-sm">{param?.title ?? settingKey}</h4>
        {param?.friendlyDescription && (
          <p className="text-xs text-main-view-fg/60 mt-0.5">
            {param.friendlyDescription}
          </p>
        )}
      </div>

      {/* Current vs Optimal */}
      {optimalValue !== undefined && (
        <div className="px-3 py-2 border-b border-main-view-fg/5 text-xs">
          <div className="flex justify-between">
            <span className="text-main-view-fg/50">Current</span>
            <span className="font-mono">{String(currentValue)}</span>
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-main-view-fg/50">Optimal</span>
            <span className="font-mono text-green-500/80">
              {String(optimalValue)}
            </span>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="py-1">
        {optimalValue !== undefined && currentValue !== optimalValue && (
          <button
            onClick={onResetToOptimal}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs
              hover:bg-main-view-fg/5 transition-colors text-left"
          >
            <IconWand size={14} className="text-main-view-fg/50" />
            Reset to optimal
          </button>
        )}
        <button
          onClick={handleCopy}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-xs
            hover:bg-main-view-fg/5 transition-colors text-left"
        >
          <IconCopy size={14} className="text-main-view-fg/50" />
          Copy value
        </button>
      </div>

      {/* Technical deep dive */}
      {param?.technicalDeepDive && (
        <div className="px-3 py-2 border-t border-main-view-fg/5 max-h-40 overflow-y-auto">
          <div className="flex items-center gap-1 mb-1">
            <IconInfoCircle size={12} className="text-main-view-fg/40" />
            <span className="text-[10px] font-medium text-main-view-fg/40 uppercase tracking-wide">
              Technical Details
            </span>
          </div>
          <p className="text-[11px] text-main-view-fg/50 leading-relaxed whitespace-pre-line">
            {param.technicalDeepDive.slice(0, 500)}
            {param.technicalDeepDive.length > 500 ? '...' : ''}
          </p>
        </div>
      )}
    </div>
  )
}

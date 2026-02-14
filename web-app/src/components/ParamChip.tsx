import {
  HoverCard,
  HoverCardTrigger,
  HoverCardContent,
} from '@/components/ui/hover-card'
import { cn } from '@/lib/utils'
import type { ParamSetting } from '@/lib/predefinedParams'

interface ParamChipProps {
  setting: ParamSetting
  isActive: boolean
  friendlyMode: boolean
  onClick: () => void
}

export default function ParamChip({
  setting,
  isActive,
  friendlyMode,
  onClick,
}: ParamChipProps) {
  const isLocalOnly = setting.compatibility.length === 1 && setting.compatibility[0] === 'local'

  return (
    <HoverCard openDelay={300} closeDelay={100}>
      <HoverCardTrigger asChild>
        <div
          onClick={onClick}
          className={cn(
            'text-xs py-1 px-2 rounded-sm cursor-pointer transition-all',
            'bg-main-view-fg/10 hover:bg-main-view-fg/15',
            isActive && 'opacity-50',
            setting.advanced && 'border border-dashed border-main-view-fg/20'
          )}
        >
          {setting.title}
        </div>
      </HoverCardTrigger>
      <HoverCardContent side="top" className="w-64 text-xs space-y-1.5">
        <div className="font-medium text-sm text-main-view-fg">
          {setting.title}
        </div>
        <p className="leading-relaxed">
          {friendlyMode ? setting.friendlyDescription : setting.description}
        </p>
        {setting.min !== undefined && setting.max !== undefined && (
          <div className="text-main-view-fg/50">
            Range: {setting.min} &ndash; {setting.max}
            {setting.step !== undefined && <> (step {setting.step})</>}
          </div>
        )}
        {isLocalOnly && (
          <div className="text-main-view-fg/40 italic">Local models only</div>
        )}
      </HoverCardContent>
    </HoverCard>
  )
}

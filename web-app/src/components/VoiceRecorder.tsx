/**
 * Voice Recorder Component
 * Microphone button with recording indicator
 */

import React from 'react'
import { Mic, MicOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface VoiceRecorderProps {
  /** Is currently recording */
  isRecording: boolean
  /** Is speech recognition supported */
  isSupported: boolean
  /** Start/stop recording callback */
  onToggle: () => void
  /** Error message */
  error?: string | null
  /** Optional className */
  className?: string
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  isRecording,
  isSupported,
  onToggle,
  error,
  className,
}) => {
  if (!isSupported) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'h-6 p-1 flex items-center justify-center rounded-sm opacity-50 cursor-not-allowed',
                className
              )}
            >
              <MicOff size={18} className="text-main-view-fg/50" />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>Voice input not supported in this browser</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            onClick={onToggle}
            className={cn(
              'h-6 p-1 flex items-center justify-center rounded-sm hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out gap-1 cursor-pointer relative',
              isRecording && 'bg-destructive/20',
              className
            )}
          >
            {isRecording ? (
              <>
                <div className="absolute inset-0 rounded-sm bg-destructive/20 animate-pulse" />
                <Mic size={18} className="text-destructive relative z-10" />
              </>
            ) : (
              <Mic size={18} className="text-main-view-fg/50" />
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            {isRecording
              ? 'Stop recording (Ctrl+M)'
              : error
                ? error
                : 'Start voice input (Ctrl+M)'}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

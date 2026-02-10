/**
 * Message Text-to-Speech Component
 * Play button for reading messages aloud
 */

import React from 'react'
import { Volume2, VolumeX, Pause } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface MessageTTSProps {
  /** Message text to speak */
  text: string
  /** Is currently speaking this message */
  isSpeaking: boolean
  /** Is paused */
  isPaused: boolean
  /** Is TTS supported */
  isSupported: boolean
  /** Start speaking callback */
  onSpeak: (text: string) => void
  /** Stop speaking callback */
  onStop: () => void
  /** Pause callback */
  onPause: () => void
  /** Resume callback */
  onResume: () => void
  /** Optional className */
  className?: string
}

export const MessageTTS: React.FC<MessageTTSProps> = ({
  text,
  isSpeaking,
  isPaused,
  isSupported,
  onSpeak,
  onStop,
  onPause,
  onResume,
  className,
}) => {
  if (!isSupported) {
    return null // Hide if not supported
  }

  const handleClick = () => {
    if (isSpeaking) {
      if (isPaused) {
        onResume()
      } else {
        onPause()
      }
    } else {
      onSpeak(text)
    }
  }

  const handleStop = (e: React.MouseEvent) => {
    e.stopPropagation()
    onStop()
  }

  return (
    <div className={cn('flex items-center gap-1', className)}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={handleClick}
              className={cn(
                'p-1.5 rounded-md hover:bg-accent transition-colors',
                isSpeaking && !isPaused && 'bg-primary/10 text-primary'
              )}
            >
              {isSpeaking && !isPaused ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              {isSpeaking
                ? isPaused
                  ? 'Resume'
                  : 'Pause'
                : 'Read aloud'}
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {isSpeaking && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={handleStop}
                className="p-1.5 rounded-md hover:bg-destructive/10 hover:text-destructive transition-colors"
              >
                <VolumeX className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Stop</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  )
}

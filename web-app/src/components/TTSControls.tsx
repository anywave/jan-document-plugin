import { useState } from 'react'
import { Volume2, Square, Save, ChevronDown, Loader2 } from 'lucide-react'
import { useTTS, VOICE_PROFILES } from '@/hooks/useTTS'
import { toast } from 'sonner'

interface TTSControlsProps {
  text: string
  threadTitle?: string
  className?: string
}

export function TTSControls({ text, threadTitle, className = '' }: TTSControlsProps) {
  const { isPlaying, isGenerating, selectedVoiceId, setSelectedVoice, play, stop, saveLastAsFile, lastGeneratedPath } = useTTS()
  const [showVoiceMenu, setShowVoiceMenu] = useState(false)

  const selectedVoice = VOICE_PROFILES.find((v) => v.id === selectedVoiceId) || VOICE_PROFILES[0]

  const handlePlay = async () => {
    if (isPlaying) {
      stop()
      return
    }
    try {
      await play(text, threadTitle)
    } catch (err) {
      toast.error('Failed to generate speech')
    }
  }

  const handleSave = async () => {
    if (!lastGeneratedPath) {
      // Generate first, then save
      try {
        await play(text, threadTitle)
        // Small delay for the file to be written
        setTimeout(async () => {
          try {
            await saveLastAsFile()
            toast.success('Audio saved')
          } catch (err) {
            console.error('TTS save error:', err)
            toast.error('Failed to save audio')
          }
        }, 500)
      } catch (err) {
        console.error('TTS generation error:', err)
        toast.error('Failed to generate speech')
      }
      return
    }
    try {
      await saveLastAsFile()
      toast.success('Audio saved')
    } catch (err) {
      console.error('TTS save error:', err)
      toast.error('Failed to save audio')
    }
  }

  return (
    <div className={`inline-flex items-center gap-1 ${className}`}>
      {/* Play / Stop */}
      <button
        onClick={handlePlay}
        disabled={isGenerating}
        className="p-1 rounded hover:bg-main-view-fg/10 transition-colors disabled:opacity-50"
        title={isPlaying ? 'Stop' : 'Read Aloud'}
      >
        {isGenerating ? (
          <Loader2 className="h-3.5 w-3.5 text-muted-fg animate-spin" />
        ) : isPlaying ? (
          <Square className="h-3.5 w-3.5 text-primary" />
        ) : (
          <Volume2 className="h-3.5 w-3.5 text-muted-fg" />
        )}
      </button>

      {/* Voice selector */}
      <div className="relative">
        <button
          onClick={() => setShowVoiceMenu(!showVoiceMenu)}
          className="flex items-center gap-0.5 px-1 py-0.5 rounded text-[10px] text-muted-fg hover:bg-main-view-fg/10 transition-colors"
          title="Select voice"
        >
          {selectedVoice.displayName.split(' ')[0]}
          <ChevronDown className="h-2.5 w-2.5" />
        </button>

        {showVoiceMenu && (
          <div className="absolute bottom-full left-0 mb-1 bg-main-view border border-main-view-fg/20 rounded-md shadow-lg p-1 z-50 min-w-[180px]">
            {VOICE_PROFILES.map((voice) => (
              <button
                key={voice.id}
                onClick={() => {
                  setSelectedVoice(voice.id)
                  setShowVoiceMenu(false)
                }}
                className={`w-full text-left px-2 py-1.5 text-sm rounded-sm transition-colors flex items-center justify-between ${
                  voice.id === selectedVoiceId
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-main-view-fg/10'
                }`}
              >
                <span>{voice.displayName}</span>
                <span className="text-[10px] text-muted-fg">{voice.locale}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={isGenerating}
        className="p-1 rounded hover:bg-main-view-fg/10 transition-colors disabled:opacity-50"
        title="Save as MP3"
      >
        <Save className="h-3.5 w-3.5 text-muted-fg" />
      </button>
    </div>
  )
}

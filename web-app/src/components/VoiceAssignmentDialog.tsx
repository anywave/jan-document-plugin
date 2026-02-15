import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useTTS, VOICE_PROFILES } from '@/hooks/useTTS'
import { useTranslation } from '@/i18n/react-i18next-compat'

export function VoiceAssignmentDialog() {
  const pendingAssignment = useTTS((s) => s.pendingAssignment)
  const playWithAssignments = useTTS((s) => s.playWithAssignments)
  const dismissAssignment = useTTS((s) => s.dismissAssignment)

  const { t } = useTranslation()
  const [assignments, setAssignments] = useState<Record<string, string>>({})

  useEffect(() => {
    if (pendingAssignment) {
      setAssignments({ ...pendingAssignment.defaults })
    }
  }, [pendingAssignment])

  const handlePlay = () => {
    if (!pendingAssignment) return
    playWithAssignments(
      pendingAssignment.text,
      assignments,
      pendingAssignment.threadTitle
    )
  }

  return (
    <Dialog
      open={!!pendingAssignment}
      onOpenChange={(open) => {
        if (!open) dismissAssignment()
      }}
    >
      <DialogContent aria-describedby="voice-assignment-desc">
        <DialogHeader>
          <DialogTitle>{t('mobius:voiceAssignment.title')}</DialogTitle>
          <DialogDescription id="voice-assignment-desc">
            {t('mobius:voiceAssignment.description')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          {pendingAssignment?.speakers.map((speaker) => (
            <div
              key={speaker}
              className="flex items-center justify-between gap-3"
            >
              <span className="text-sm font-medium truncate min-w-0 flex-1">
                {speaker}
              </span>
              <select
                value={assignments[speaker] || ''}
                onChange={(e) =>
                  setAssignments((prev) => ({
                    ...prev,
                    [speaker]: e.target.value,
                  }))
                }
                className="bg-main-view border border-main-view-fg/20 text-main-view-fg text-sm rounded-md px-2 py-1.5 min-w-[180px]"
              >
                {VOICE_PROFILES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.displayName}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button
            variant="link"
            size="sm"
            className="hover:no-underline"
            onClick={dismissAssignment}
          >
            {t('mobius:voiceAssignment.cancel')}
          </Button>
          <Button onClick={handlePlay}>{t('mobius:voiceAssignment.play')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

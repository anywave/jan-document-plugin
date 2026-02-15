import { useState } from 'react'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { IconFolder, IconAlertTriangle } from '@tabler/icons-react'
import { useTranslation } from '@/i18n/react-i18next-compat'

interface ChangeDataFolderLocationProps {
  children: React.ReactNode
  currentPath: string
  onConfirm: () => void
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function ChangeDataFolderLocation({
  children,
  currentPath,
  onConfirm,
  open,
  onOpenChange,
}: ChangeDataFolderLocationProps) {
  const { t } = useTranslation()
  const [confirmInput, setConfirmInput] = useState('')

  const isConfirmed = confirmInput === 'I agree'

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) setConfirmInput('')
    onOpenChange(nextOpen)
  }

  const handleConfirm = () => {
    if (!isConfirmed) return
    setConfirmInput('')
    onConfirm()
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <IconFolder size={20} />
            {t('settings:dialogs.changeDataFolder.title')}
          </DialogTitle>
          <DialogDescription>
            {t('settings:dialogs.changeDataFolder.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Warning block */}
          <div className="flex gap-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
            <IconAlertTriangle
              size={20}
              className="shrink-0 text-amber-500 mt-0.5"
            />
            <p className="text-sm text-main-view-fg/80 leading-relaxed">
              {t('settings:dialogs.changeDataFolder.warning')}
            </p>
          </div>

          <div>
            <h4 className="text-sm font-medium text-main-view-fg/80 mb-2">
              {t('settings:dialogs.changeDataFolder.currentLocation')}
            </h4>
            <div className="bg-main-view-fg/5 border border-main-view-fg/10 rounded">
              <code className="text-xs text-main-view-fg/70 break-all">
                {currentPath}
              </code>
            </div>
          </div>

          {/* "I agree" confirmation input */}
          <div>
            <label className="text-sm text-main-view-fg/70 mb-2 block">
              {t('settings:dialogs.changeDataFolder.confirmPrompt')}
            </label>
            <Input
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder={t(
                'settings:dialogs.changeDataFolder.confirmPlaceholder'
              )}
              className="text-sm"
            />
          </div>
        </div>

        <DialogFooter className="flex items-center gap-2">
          <DialogClose asChild>
            <Button variant="link" size="sm">
              {t('settings:dialogs.changeDataFolder.cancel')}
            </Button>
          </DialogClose>
          <Button onClick={handleConfirm} disabled={!isConfirmed}>
            {t('settings:dialogs.changeDataFolder.changeLocation')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

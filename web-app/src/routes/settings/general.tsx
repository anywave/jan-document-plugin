import { createFileRoute } from '@tanstack/react-router'
import { route } from '@/constants/routes'
import SettingsMenu from '@/containers/SettingsMenu'
import HeaderPage from '@/containers/HeaderPage'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Card, CardItem } from '@/containers/Card'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { useGeneralSetting } from '@/hooks/useGeneralSetting'
import { lazy, Suspense, useEffect, useState } from 'react'
import { open } from '@tauri-apps/plugin-dialog'
import { openUrl, revealItemInDir } from '@tauri-apps/plugin-opener'
import ChangeDataFolderLocation from '@/containers/dialogs/ChangeDataFolderLocation'

import {
  getJanDataFolder,
  relocateJanDataFolder,
} from '@/services/app'
import {
  IconExternalLink,
  IconFolder,
  IconLogs,
  IconCopy,
  IconCopyCheck,
} from '@tabler/icons-react'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'
import { windowKey } from '@/constants/windows'
import { toast } from 'sonner'
import { emit } from '@tauri-apps/api/event'
import { stopAllModels } from '@/services/models'
import { SystemEvent } from '@/types/events'
import { Input } from '@/components/ui/input'
import { getConnectedServers } from '@/services/mcp'
import { invoke } from '@tauri-apps/api/core'
import { useMCPServers } from '@/hooks/useMCPServers'
import { Dialog, DialogContent } from '@/components/ui/dialog'

const ExportMobiusDialog = lazy(() => import('@/containers/dialogs/ExportMobiusDialog'))
const ImportMobiusDialog = lazy(() => import('@/containers/dialogs/ImportMobiusDialog'))

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute(route.settings.general as any)({
  component: General,
})

function General() {
  const { t } = useTranslation()
  const {
    spellCheckChatInput,
    setSpellCheckChatInput,
    experimentalFeatures,
    setExperimentalFeatures,
  } = useGeneralSetting()

  const openFileTitle = (): string => {
    if (IS_MACOS) {
      return t('settings:general.showInFinder')
    } else if (IS_WINDOWS) {
      return t('settings:general.showInFileExplorer')
    } else {
      return t('settings:general.openContainingFolder')
    }
  }
  const [janDataFolder, setJanDataFolder] = useState<string | undefined>()
  const [isCopied, setIsCopied] = useState(false)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [experimentalAllowed, setExperimentalAllowed] = useState(false)
  const [showMobiusExport, setShowMobiusExport] = useState(false)
  const [showMobiusImport, setShowMobiusImport] = useState(false)
  useEffect(() => {
    const fetchDataFolder = async () => {
      const path = await getJanDataFolder()
      setJanDataFolder(path)

      // Check if experimental features are allowed via shared marker file
      try {
        const allowed = await invoke<boolean>('exists_sync', {
          args: ['file://.experimental-features'],
        })
        setExperimentalAllowed(allowed)
      } catch {
        setExperimentalAllowed(false)
      }
    }

    fetchDataFolder()
  }, [])

  const handleOpenLogs = async () => {
    try {
      // Check if logs window already exists
      const existingWindow = await WebviewWindow.getByLabel(
        windowKey.logsAppWindow
      )

      if (existingWindow) {
        // If window exists, focus it
        await existingWindow.setFocus()
        // focused existing logs window
      } else {
        // Create a new logs window using Tauri v2 WebviewWindow API
        const logsWindow = new WebviewWindow(windowKey.logsAppWindow, {
          url: route.appLogs,
          title: 'App Logs - Jan',
          width: 800,
          height: 600,
          resizable: true,
          center: true,
        })

        // Listen for window creation
        logsWindow.once('tauri://created', () => {
          // window ready
        })

        // Listen for window errors
        logsWindow.once('tauri://error', (e) => {
          console.error('Error creating logs window:', e)
        })
      }
    } catch (error) {
      console.error('Failed to open logs window:', error)
    }
  }

  const handleOpenDocs = async () => {
    try {
      const existing = await WebviewWindow.getByLabel(windowKey.docsWindow)
      if (existing) {
        await existing.setFocus()
      } else {
        new WebviewWindow(windowKey.docsWindow, {
          url: '/docs/index.html',
          title: 'MOBIUS Documentation',
          width: 960,
          height: 700,
          resizable: true,
          center: true,
        })
      }
    } catch (error) {
      console.error('Failed to open docs window:', error)
    }
  }

  const handleOpenReleaseNotes = async () => {
    try {
      const existing = await WebviewWindow.getByLabel(
        windowKey.releaseNotesWindow
      )
      if (existing) {
        await existing.setFocus()
      } else {
        new WebviewWindow(windowKey.releaseNotesWindow, {
          url: '/docs/release-notes.html',
          title: 'MOBIUS Release Notes',
          width: 960,
          height: 700,
          resizable: true,
          center: true,
        })
      }
    } catch (error) {
      console.error('Failed to open release notes window:', error)
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000) // Reset after 2 seconds
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
  }

  const handleDataFolderChange = () => {
    setIsDialogOpen(true)
  }

  const confirmDataFolderChange = async () => {
    setIsDialogOpen(false)

    const selectedPath = await open({
      multiple: false,
      directory: true,
      defaultPath: janDataFolder,
    })

    if (selectedPath === janDataFolder || selectedPath === null) return

    try {
      await stopAllModels()
      emit(SystemEvent.KILL_SIDECAR)
      setTimeout(async () => {
        try {
          await relocateJanDataFolder(selectedPath)
          setJanDataFolder(selectedPath)
          window.core?.api?.relaunch()
        } catch (error) {
          console.error(error)
          toast.error(t('settings:general.failedToRelocateDataFolder'))
        }
      }, 1000)
    } catch (error) {
      console.error('Failed to relocate data folder:', error)
      const originalPath = await getJanDataFolder()
      setJanDataFolder(originalPath)
      toast.error(t('settings:general.failedToRelocateDataFolderDesc'))
    }
  }

  const handleStopAllMCPServers = async () => {
    try {
      const connectedServers = await getConnectedServers()

      // Stop each connected server
      const stopPromises = connectedServers.map((serverName) =>
        invoke('deactivate_mcp_server', { name: serverName }).catch((error) => {
          console.error(`Error stopping MCP server ${serverName}:`, error)
          return Promise.resolve() // Continue with other servers even if one fails
        })
      )

      await Promise.all(stopPromises)

      // Update server configs to set active: false for stopped servers
      const { mcpServers, editServer } = useMCPServers.getState()
      connectedServers.forEach((serverName) => {
        const serverConfig = mcpServers[serverName]
        if (serverConfig) {
          editServer(serverName, { ...serverConfig, active: false })
        }
      })

      if (connectedServers.length > 0) {
        toast.success(`Stopped ${connectedServers.length} MCP server(s)`)
      }
    } catch (error) {
      console.error('Error stopping MCP servers:', error)
      toast.error('Failed to stop MCP servers')
    }
  }

  return (
    <div className="flex flex-col h-full">
      <HeaderPage>
        <h1 className="font-medium">{t('common:settings')}</h1>
      </HeaderPage>
      <div className="flex h-full w-full flex-col sm:flex-row">
        <SettingsMenu />
        <div className="p-4 w-full h-[calc(100%-32px)] overflow-y-auto">
          <div className="flex flex-col justify-between gap-4 gap-y-3 w-full">
            {/* General */}
            <Card title={t('common:general')}>
              <CardItem
                title={t('settings:general.appVersion')}
                actions={
                  <span className="text-main-view-fg/80 font-medium">
                    v{VERSION}⋈{MOBIUS_RELEASE}
                  </span>
                }
              />
              <CardItem
                title={t('settings:general.checkForUpdates')}
                description={t('settings:general.checkForUpdatesDesc')}
                className="flex-col sm:flex-row items-start sm:items-center sm:justify-between gap-y-2"
                actions={
                  <Button
                    variant="link"
                    size="sm"
                    className="p-0"
                    onClick={() =>
                      openUrl('https://github.com/anywave/mobius/releases')
                    }
                  >
                    <div className="cursor-pointer rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                      {t('settings:general.viewReleases')}
                    </div>
                  </Button>
                }
              />
              {/* <CardItem
                title={t('common:language')}
                actions={<LanguageSwitcher />}
              /> */}
            </Card>

            {/* Data folder */}
            <Card title={t('common:dataFolder')}>
              <CardItem
                title={t('settings:dataFolder.appData', {
                  ns: 'settings',
                })}
                align="start"
                className="flex-col sm:flex-row items-start sm:items-center sm:justify-between gap-y-2"
                description={
                  <>
                    <span>
                      {t('settings:dataFolder.appDataDesc', {
                        ns: 'settings',
                      })}
                      &nbsp;
                    </span>
                    <div className="flex items-center gap-2 mt-1 ">
                      <div className="">
                        <span
                          title={janDataFolder}
                          className="bg-main-view-fg/10 text-xs px-1 py-0.5 rounded-sm text-main-view-fg/80 line-clamp-1 w-fit"
                        >
                          {janDataFolder}
                        </span>
                      </div>
                      <button
                        onClick={() =>
                          janDataFolder && copyToClipboard(janDataFolder)
                        }
                        className="cursor-pointer flex items-center justify-center rounded hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out p-1"
                        title={
                          isCopied
                            ? t('settings:general.copied')
                            : t('settings:general.copyPath')
                        }
                      >
                        {isCopied ? (
                          <div className="flex items-center gap-1">
                            <IconCopyCheck size={12} className="text-accent" />
                            <span className="text-xs leading-0">
                              {t('settings:general.copied')}
                            </span>
                          </div>
                        ) : (
                          <IconCopy
                            size={12}
                            className="text-main-view-fg/50"
                          />
                        )}
                      </button>
                    </div>
                  </>
                }
                actions={
                  <>
                    <Button
                      variant="link"
                      size="sm"
                      className="p-0"
                      title={t('settings:dataFolder.appData')}
                      onClick={handleDataFolderChange}
                    >
                      <div className="cursor-pointer flex items-center justify-center rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                        <IconFolder
                          size={12}
                          className="text-main-view-fg/50"
                        />
                        <span>{t('settings:general.changeLocation')}</span>
                      </div>
                    </Button>
                    <ChangeDataFolderLocation
                      currentPath={janDataFolder || ''}
                      onConfirm={confirmDataFolderChange}
                      open={isDialogOpen}
                      onOpenChange={setIsDialogOpen}
                    >
                      <div />
                    </ChangeDataFolderLocation>
                  </>
                }
              />
              <CardItem
                title={t('settings:dataFolder.appLogs', {
                  ns: 'settings',
                })}
                description={t('settings:dataFolder.appLogsDesc')}
                className="flex-col sm:flex-row items-start sm:items-center sm:justify-between gap-y-2"
                actions={
                  <div className="flex items-center gap-2">
                    <Button
                      variant="link"
                      size="sm"
                      className="p-0"
                      onClick={handleOpenLogs}
                      title={t('settings:dataFolder.appLogs')}
                    >
                      <div className="cursor-pointer flex items-center justify-center rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                        <IconLogs size={12} className="text-main-view-fg/50" />
                        <span>{t('settings:general.openLogs')}</span>
                      </div>
                    </Button>
                    <Button
                      variant="link"
                      size="sm"
                      className="p-0"
                      onClick={async () => {
                        if (janDataFolder) {
                          try {
                            const logsPath = `${janDataFolder}/logs`
                            await revealItemInDir(logsPath)
                          } catch (error) {
                            console.error(
                              'Failed to reveal logs folder:',
                              error
                            )
                          }
                        }
                      }}
                      title={t('settings:general.revealLogs')}
                    >
                      <div className="cursor-pointer flex items-center justify-center rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                        <IconFolder
                          size={12}
                          className="text-main-view-fg/50"
                        />
                        <span>{openFileTitle()}</span>
                      </div>
                    </Button>
                  </div>
                }
              />
            </Card>
            {/* Import & Export */}
            <Card title={t('sharing:importExport')}>
              <CardItem
                title={t('sharing:exportAsMobius')}
                description="Export assistants, threads, and knowledge as a shareable .mobius package"
                actions={
                  <Button
                    variant="link"
                    size="sm"
                    className="p-0"
                    onClick={() => setShowMobiusExport(true)}
                  >
                    <div className="cursor-pointer rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                      {t('sharing:export')}
                    </div>
                  </Button>
                }
              />
              <CardItem
                title={t('sharing:importMobius')}
                description="Import assistants, threads, and knowledge from a .mobius package"
                actions={
                  <Button
                    variant="link"
                    size="sm"
                    className="p-0"
                    onClick={() => setShowMobiusImport(true)}
                  >
                    <div className="cursor-pointer rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                      {t('sharing:import')}
                    </div>
                  </Button>
                }
              />
            </Card>

            {/* Advanced */}
            <Card title="Advanced">
              <CardItem
                title="Experimental Features"
                description={
                  experimentalAllowed
                    ? 'Enable experimental features. They may be unstable or change at any time.'
                    : 'Experimental features must be enabled in Jan first. Place a .experimental-features file in the shared data folder to unlock.'
                }
                actions={
                  <Switch
                    checked={experimentalFeatures && experimentalAllowed}
                    disabled={!experimentalAllowed}
                    onCheckedChange={async (e) => {
                      if (!experimentalAllowed) return
                      await handleStopAllMCPServers()
                      setExperimentalFeatures(e)
                    }}
                  />
                }
              />
            </Card>

            {/* Other */}
            <Card title={t('common:others')}>
              <CardItem
                title={t('settings:others.spellCheck', {
                  ns: 'settings',
                })}
                description={t('settings:others.spellCheckDesc', {
                  ns: 'settings',
                })}
                actions={
                  <Switch
                    checked={spellCheckChatInput}
                    onCheckedChange={(e) => setSpellCheckChatInput(e)}
                  />
                }
              />
            </Card>

            {/* Resources */}
            <Card title={t('settings:general.resources')}>
              <CardItem
                title={t('settings:general.documentation')}
                description={t('settings:general.documentationDesc')}
                actions={
                  <Button
                    variant="link"
                    size="sm"
                    className="p-0"
                    onClick={handleOpenDocs}
                  >
                    <div className="cursor-pointer rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                      {t('settings:general.viewDocs')}
                    </div>
                  </Button>
                }
              />
              <CardItem
                title={t('settings:general.releaseNotes')}
                description={t('settings:general.releaseNotesDesc')}
                actions={
                  <Button
                    variant="link"
                    size="sm"
                    className="p-0"
                    onClick={handleOpenReleaseNotes}
                  >
                    <div className="cursor-pointer rounded-sm hover:bg-main-view-fg/15 bg-main-view-fg/10 transition-all duration-200 ease-in-out px-2 py-1 gap-1">
                      {t('settings:general.viewReleases')}
                    </div>
                  </Button>
                }
              />
            </Card>

            {/* Support */}
            <Card title={t('settings:general.support')}>
              <CardItem
                title="Report an Issue"
                description="Report bugs or request features on GitHub"
                actions={
                  <a
                    href="https://github.com/anywave/mobius/issues"
                    target="_blank"
                  >
                    <div className="flex items-center gap-1">
                      <span>Report Issue</span>
                      <IconExternalLink size={14} />
                    </div>
                  </a>
                }
              />
            </Card>
          </div>
        </div>
      </div>

      {/* .mobius Export Dialog */}
      <Dialog open={showMobiusExport} onOpenChange={setShowMobiusExport}>
        <DialogContent>
          <Suspense fallback={null}>
            <ExportMobiusDialog onClose={() => setShowMobiusExport(false)} />
          </Suspense>
        </DialogContent>
      </Dialog>

      {/* .mobius Import Dialog */}
      <Dialog open={showMobiusImport} onOpenChange={setShowMobiusImport}>
        <DialogContent>
          <Suspense fallback={null}>
            <ImportMobiusDialog
              onClose={() => setShowMobiusImport(false)}
              onImported={() => {
                // Trigger a page reload to refresh thread list
                window.location.reload()
              }}
            />
          </Suspense>
        </DialogContent>
      </Dialog>
    </div>
  )
}

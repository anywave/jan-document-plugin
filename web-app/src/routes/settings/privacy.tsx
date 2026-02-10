import { createFileRoute } from '@tanstack/react-router'
import { route } from '@/constants/routes'
import SettingsMenu from '@/containers/SettingsMenu'
import HeaderPage from '@/containers/HeaderPage'
import { Card, CardItem } from '@/containers/Card'
import { useTranslation } from '@/i18n/react-i18next-compat'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute(route.settings.privacy as any)({
  component: Privacy,
})

function Privacy() {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col h-full">
      <HeaderPage>
        <h1 className="font-medium">{t('common:settings')}</h1>
      </HeaderPage>
      <div className="flex h-full w-full">
        <SettingsMenu />
        <div className="p-4 w-full h-[calc(100%-32px)] overflow-y-auto">
          <div className="flex flex-col justify-between gap-4 gap-y-3 w-full">
            <Card
              header={
                <div className="flex items-center justify-between mb-4">
                  <h1 className="text-main-view-fg font-medium text-base">
                    Privacy Policy
                  </h1>
                </div>
              }
            >
              <CardItem
                description={
                  <div className="text-main-view-fg/90">
                    <p className="mb-4">
                      MOBIUS is committed to your privacy. This application operates 100% offline with no data collection, tracking, or telemetry of any kind.
                    </p>
                    <p className="mb-2 font-medium">Your Privacy Guarantees:</p>
                    <ul className="list-disc pl-4 space-y-1">
                      <li className="font-medium">
                        No data is sent to external servers
                      </li>
                      <li className="font-medium">
                        No analytics or tracking
                      </li>
                      <li className="font-medium">
                        All processing happens locally on your device
                      </li>
                      <li className="font-medium">
                        Your conversations and documents never leave your computer
                      </li>
                      <li className="font-medium">
                        No crash reporting or diagnostics collection
                      </li>
                    </ul>
                    <p className="mt-4">
                      For more information, visit:{' '}
                      <a
                        href="https://anywave.com/privacy"
                        className="text-accent hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        https://anywave.com/privacy
                      </a>
                    </p>
                  </div>
                }
              />
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

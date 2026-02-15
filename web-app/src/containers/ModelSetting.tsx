import { useMemo, useCallback, useState } from 'react'
import { IconSettings, IconWand, IconInfoCircle } from '@tabler/icons-react'
import debounce from 'lodash.debounce'

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { DynamicControllerSetting } from '@/containers/dynamicControllerSetting'
import { useModelProvider } from '@/hooks/useModelProvider'
import { useHardware } from '@/hooks/useHardware'
import { stopModel } from '@/services/models'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { getOptimalSettingsForUI, type OptimalSettingsForUI } from '@/lib/modelOptimizer'
import { paramsSettings } from '@/lib/predefinedParams'
import { SettingContextMenu } from '@/components/SettingContextMenu'

type ModelSettingProps = {
  provider: ProviderObject
  model: Model
  smallIcon?: boolean
}

export function ModelSetting({
  model,
  provider,
  smallIcon,
}: ModelSettingProps) {
  const { updateProvider } = useModelProvider()
  const { hardwareData } = useHardware()
  const { t } = useTranslation()
  const [contextMenu, setContextMenu] = useState<{
    key: string
    x: number
    y: number
  } | null>(null)

  // Compute optimal settings from hardware profile
  const optimal: OptimalSettingsForUI | null = useMemo(() => {
    if (!hardwareData?.cpu?.core_count) return null
    try {
      return getOptimalSettingsForUI(model.id, hardwareData)
    } catch {
      return null
    }
  }, [model.id, hardwareData])

  // Create a debounced version of stopModel that waits 500ms after the last call
  const debouncedStopModel = debounce((modelId: string) => {
    stopModel(modelId)
  }, 500)

  const handleSettingChange = (
    key: string,
    value: string | boolean | number
  ) => {
    if (!provider) return

    // Create a copy of the model with updated settings
    const updatedModel = {
      ...model,
      settings: {
        ...model.settings,
        [key]: {
          ...(model.settings?.[key] != null ? model.settings?.[key] : {}),
          controller_props: {
            ...(model.settings?.[key]?.controller_props ?? {}),
            value: value,
          },
        },
      },
    }

    // Find the model index in the provider's models array
    const modelIndex = provider.models.findIndex((m) => m.id === model.id)

    if (modelIndex !== -1) {
      // Create a copy of the provider's models array
      const updatedModels = [...provider.models]

      // Update the specific model in the array
      updatedModels[modelIndex] = updatedModel as Model

      // Update the provider with the new models array
      updateProvider(provider.provider, {
        models: updatedModels,
      })

      // Call debounced stopModel only when updating ctx_len or ngl
      if (key === 'ctx_len' || key === 'ngl' || key === 'chat_template') {
        debouncedStopModel(model.id)
      }
    }
  }

  const handleResetToOptimal = useCallback(() => {
    if (!optimal || !provider) return

    const modelIndex = provider.models.findIndex((m) => m.id === model.id)
    if (modelIndex === -1) return

    const updatedSettings = { ...model.settings }
    for (const [key, optimalValue] of Object.entries(optimal.values)) {
      if (updatedSettings[key]) {
        updatedSettings[key] = {
          ...updatedSettings[key],
          controller_props: {
            ...(updatedSettings[key] as ProviderSetting).controller_props,
            value: optimalValue,
          },
        }
      }
    }

    const updatedModels = [...provider.models]
    updatedModels[modelIndex] = {
      ...model,
      settings: updatedSettings,
    } as Model

    updateProvider(provider.provider, { models: updatedModels })
    debouncedStopModel(model.id)
  }, [optimal, provider, model, updateProvider, debouncedStopModel])

  const isOptimal = useCallback(
    (key: string): boolean | null => {
      if (!optimal?.values[key] === undefined) return null
      const currentValue = (model.settings?.[key] as ProviderSetting)
        ?.controller_props?.value
      if (currentValue === undefined) return null
      return currentValue === optimal?.values[key]
    },
    [optimal, model.settings]
  )

  const handleContextMenu = (e: React.MouseEvent, key: string) => {
    e.preventDefault()
    setContextMenu({ key, x: e.clientX, y: e.clientY })
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <div
          className={cn(
            'size-6 cursor-pointer flex items-center justify-center rounded hover:bg-main-view-fg/10 transition-all duration-200 ease-in-out',
            smallIcon && 'size-5'
          )}
        >
          <IconSettings size={18} className="text-main-view-fg/50" />
        </div>
      </SheetTrigger>
      <SheetContent className="h-[calc(100%-8px)] top-1 right-1 rounded-e-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            {t('common:modelSettings.title', { modelId: model.id })}
          </SheetTitle>
          <SheetDescription>
            {t('common:modelSettings.description')}
          </SheetDescription>
        </SheetHeader>

        {/* Reset to Optimal button */}
        {optimal && (
          <div className="px-4 pb-2">
            <button
              onClick={handleResetToOptimal}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md
                bg-main-view-fg/5 hover:bg-main-view-fg/10 text-main-view-fg/70
                transition-colors duration-150"
            >
              <IconWand size={14} />
              Reset to optimal ({optimal.tier})
            </button>
            <p className="text-main-view-fg/40 text-[10px] mt-1">
              {optimal.summary}
            </p>
          </div>
        )}

        <div className="px-4 space-y-6">
          {Object.entries(model.settings || {}).map(([key, value]) => {
            const config = value as ProviderSetting
            const optimalMatch = isOptimal(key)

            return (
              <div
                key={key}
                className="space-y-2"
                onContextMenu={(e) => handleContextMenu(e, key)}
              >
                <div
                  className={cn(
                    'flex items-start justify-between gap-8 last:mb-2',
                    (key === 'chat_template' ||
                      key === 'override_tensor_buffer_t') &&
                      'flex-col gap-1 w-full'
                  )}
                >
                  <div className="space-y-1 mb-2">
                    <div className="flex items-center gap-1.5">
                      <h3 className="font-medium">{config.title}</h3>
                      {optimalMatch === false && (
                        <span
                          className="size-1.5 rounded-full bg-amber-400 shrink-0"
                          title={`Optimal: ${optimal?.values[key]}`}
                        />
                      )}
                    </div>
                    <p className="text-main-view-fg/70 text-xs">
                      {config.description}
                    </p>
                  </div>
                  <DynamicControllerSetting
                    key={config.key}
                    title={config.title}
                    description={config.description}
                    controllerType={config.controller_type}
                    controllerProps={{
                      ...config.controller_props,
                      value: config.controller_props?.value,
                    }}
                    onChange={(newValue) => handleSettingChange(key, newValue)}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Context menu */}
        {contextMenu && (
          <SettingContextMenu
            settingKey={contextMenu.key}
            currentValue={
              (model.settings?.[contextMenu.key] as ProviderSetting)
                ?.controller_props?.value
            }
            optimalValue={optimal?.values[contextMenu.key]}
            position={{ x: contextMenu.x, y: contextMenu.y }}
            onClose={() => setContextMenu(null)}
            onResetToOptimal={() => {
              if (optimal?.values[contextMenu.key] !== undefined) {
                handleSettingChange(
                  contextMenu.key,
                  optimal.values[contextMenu.key]
                )
              }
              setContextMenu(null)
            }}
          />
        )}
      </SheetContent>
    </Sheet>
  )
}

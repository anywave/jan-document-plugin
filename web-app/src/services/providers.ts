import { models as providerModels } from 'token.js'
import { predefinedProviders } from '@/consts/providers'
import { SettingComponentProps } from '@janhq/core'
import {
  DefaultToolUseSupportedModels,
  ModelCapabilities,
} from '@/types/models'
import { modelSettings } from '@/lib/predefined'
import { fetchModels } from './models'
import { ExtensionManager } from '@/lib/extension'
import { fetch as fetchTauri } from '@tauri-apps/plugin-http'
import { invoke } from '@tauri-apps/api/core'

interface ModelYml {
  model_path?: string
  name?: string
  size_bytes?: number
}

/**
 * Scan llamacpp/models/ directory directly for model.yml files
 */
const scanLocalModels = async (): Promise<Array<{ id: string; name: string }>> => {
  try {
    const janDataPath = await invoke<string>('get_jan_data_folder_path')
    const modelsDir = `${janDataPath}/llamacpp/models`

    // List directories in models folder
    const entries = await invoke<Array<{ path: string; name: string; is_dir: boolean }>>(
      'list_dir', { path: modelsDir }
    )

    const models: Array<{ id: string; name: string }> = []
    for (const entry of entries) {
      if (entry.is_dir) {
        try {
          const ymlPath = `${entry.path}/model.yml`
          const yml = await invoke<ModelYml>('read_yaml', { path: ymlPath })
          models.push({
            id: entry.name,
            name: yml.name || entry.name,
          })
        } catch {
          // No model.yml in this directory, skip
        }
      }
    }
    return models
  } catch (error) {
    console.warn('Failed to scan local models via invoke:', error)
    return []
  }
}

export const getProviders = async (): Promise<ModelProvider[]> => {
  // Hardcoded llamacpp provider with known local models
  return [{
    active: true,
    persist: true,
    provider: 'llamacpp',
    base_url: '',
    settings: [],
    models: [
      {
        id: 'jan-nano-128k-iQ4_XS.gguf',
        model: 'jan-nano-128k-iQ4_XS.gguf',
        name: 'Jan Nano 128k',
        description: '',
        capabilities: [ModelCapabilities.COMPLETION],
        provider: 'llamacpp',
        settings: Object.values(modelSettings).reduce(
          (acc, setting) => {
            let value = setting.controller_props.value
            if (setting.key === 'ctx_len') value = 8192
            acc[setting.key] = {
              ...setting,
              controller_props: { ...setting.controller_props, value },
            }
            return acc
          },
          {} as Record<string, ProviderSetting>
        ),
      },
      {
        id: 'jan-nano-4b-iQ4_XS.gguf',
        model: 'jan-nano-4b-iQ4_XS.gguf',
        name: 'Jan Nano 4B',
        description: '',
        capabilities: [ModelCapabilities.COMPLETION],
        provider: 'llamacpp',
        settings: Object.values(modelSettings).reduce(
          (acc, setting) => {
            let value = setting.controller_props.value
            if (setting.key === 'ctx_len') value = 8192
            acc[setting.key] = {
              ...setting,
              controller_props: { ...setting.controller_props, value },
            }
            return acc
          },
          {} as Record<string, ProviderSetting>
        ),
      },
      {
        id: 'Jan-v1-edge-Q4_K_M',
        model: 'Jan-v1-edge-Q4_K_M',
        name: 'Jan V1 Edge',
        description: '',
        capabilities: [ModelCapabilities.COMPLETION],
        provider: 'llamacpp',
        settings: Object.values(modelSettings).reduce(
          (acc, setting) => {
            let value = setting.controller_props.value
            if (setting.key === 'ctx_len') value = 8192
            acc[setting.key] = {
              ...setting,
              controller_props: { ...setting.controller_props, value },
            }
            return acc
          },
          {} as Record<string, ProviderSetting>
        ),
      },
    ],
  } as ModelProvider]
}

/**
 * Fetches models from a provider's API endpoint
 * Always uses Tauri's HTTP client to bypass CORS issues
 * @param provider The provider object containing base_url and api_key
 * @returns Promise<string[]> Array of model IDs
 */
export const fetchModelsFromProvider = async (
  provider: ModelProvider
): Promise<string[]> => {
  if (!provider.base_url) {
    throw new Error('Provider must have base_url configured')
  }

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // Only add authentication headers if API key is provided
    if (provider.api_key) {
      headers['x-api-key'] = provider.api_key
      headers['Authorization'] = `Bearer ${provider.api_key}`
    }

    // Always use Tauri's fetch to avoid CORS issues
    const response = await fetchTauri(`${provider.base_url}/models`, {
      method: 'GET',
      headers,
    })

    if (!response.ok) {
      throw new Error(
        `Failed to fetch models: ${response.status} ${response.statusText}`
      )
    }

    const data = await response.json()

    // Handle different response formats that providers might use
    if (data.data && Array.isArray(data.data)) {
      // OpenAI format: { data: [{ id: "model-id" }, ...] }
      return data.data.map((model: { id: string }) => model.id).filter(Boolean)
    } else if (Array.isArray(data)) {
      // Direct array format: ["model-id1", "model-id2", ...]
      return data
        .filter(Boolean)
        .map((model) =>
          typeof model === 'object' && 'id' in model ? model.id : model
        )
    } else if (data.models && Array.isArray(data.models)) {
      // Alternative format: { models: [...] }
      return data.models
        .map((model: string | { id: string }) =>
          typeof model === 'string' ? model : model.id
        )
        .filter(Boolean)
    } else {
      console.warn('Unexpected response format from provider API:', data)
      return []
    }
  } catch (error) {
    console.error('Error fetching models from provider:', error)

    // Provide helpful error message
    if (error instanceof Error && error.message.includes('fetch')) {
      throw new Error(
        `Cannot connect to ${provider.provider} at ${provider.base_url}. Please check that the service is running and accessible.`
      )
    }

    throw error
  }
}

/**
 * Update the settings of a provider extension.
 * TODO: Later on we don't retrieve this using provider name
 * @param providerName
 * @param settings
 */
export const updateSettings = async (
  providerName: string,
  settings: ProviderSetting[]
): Promise<void> => {
  return ExtensionManager.getInstance()
    .getEngine(providerName)
    ?.updateSettings(
      settings.map((setting) => ({
        ...setting,
        controllerProps: {
          ...setting.controller_props,
          value:
            setting.controller_props.value !== undefined
              ? setting.controller_props.value
              : '',
        },
        controllerType: setting.controller_type,
      })) as SettingComponentProps[]
    )
}

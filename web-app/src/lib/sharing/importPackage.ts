/**
 * Import .mobius packages — preview contents, check models, import selected items.
 */

import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'
import { useAssistant } from '@/hooks/useAssistant'

/** Open a file picker and preview a .mobius package */
export async function pickAndPreviewPackage(): Promise<MobiusImportPreview | null> {
  const filePath = await open({
    multiple: false,
    filters: [{ name: 'MOBIUS Package', extensions: ['mobius'] }],
  })

  if (!filePath) return null

  return previewPackage(filePath as string)
}

/** Preview a .mobius package at the given path */
export async function previewPackage(
  packagePath: string
): Promise<MobiusImportPreview> {
  const result = await invoke<{
    manifest: MobiusManifest
    assistants: ExportableAssistant[]
    threads: ExportableThread[]
    knowledge: { collection: string; chunkCount: number }[]
  }>('read_mobius_package', { packagePath })

  // Check which referenced models are available locally
  const modelWarnings: string[] = []
  for (const modelId of result.manifest.modelRefs || []) {
    // A simple heuristic: check if any thread or assistant references a model
    // that isn't in the known installed models. We can't check the model store
    // from here without coupling, so we surface all refs as potential warnings.
    modelWarnings.push(modelId)
  }

  return {
    ...result,
    modelWarnings,
  }
}

/** Import selected items from a previewed package */
export async function importFromPackage(
  options: MobiusImportOptions
): Promise<{
  importedAssistants: number
  importedThreads: number
  importedKnowledgeChunks: number
  assistants: ExportableAssistant[]
  threads: ExportableThread[]
}> {
  const result = await invoke<{
    importedAssistants: number
    importedThreads: number
    importedKnowledgeChunks: number
    assistants: ExportableAssistant[]
    threads: Record<string, unknown>[]
  }>('import_mobius_package', {
    packagePath: options.packagePath,
    assistantIds: options.assistantIds,
    threadIds: options.threadIds,
    knowledgeCollections: options.knowledgeCollections,
  })

  // Refresh the assistant store with imported assistants
  if (result.assistants.length > 0) {
    const store = useAssistant.getState()
    for (const imported of result.assistants) {
      const existing = store.assistants.find((a) => a.id === imported.id)
      if (!existing) {
        store.addAssistant(imported as unknown as Assistant)
      }
    }
  }

  return {
    importedAssistants: result.importedAssistants,
    importedThreads: result.importedThreads,
    importedKnowledgeChunks: result.importedKnowledgeChunks,
    assistants: result.assistants,
    threads: result.threads as unknown as ExportableThread[],
  }
}

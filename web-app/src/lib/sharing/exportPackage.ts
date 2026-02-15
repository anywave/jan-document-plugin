/**
 * Export .mobius packages — gathers data from stores, sanitizes, and invokes Rust zip.
 */

import { invoke } from '@tauri-apps/api/core'
import { save } from '@tauri-apps/plugin-dialog'
import { useAssistant } from '@/hooks/useAssistant'
import { useThreads } from '@/hooks/useThreads'
import { fetchMessages } from '@/services/messages'
import {
  sanitizeAssistant,
  sanitizeThread,
  sanitizeMessage,
} from './sanitize'

/** Build and save a .mobius package from the given options */
export async function exportMobiusPackage(
  options: MobiusExportOptions
): Promise<string | null> {
  const assistantStore = useAssistant.getState()
  const threadStore = useThreads.getState()

  // Gather assistants
  const exportableAssistants: ExportableAssistant[] = options.assistantIds
    .map((id) => assistantStore.assistants.find((a) => a.id === id))
    .filter((a): a is Assistant => a !== undefined)
    .map((a) => sanitizeAssistant(a, options.includeInstructions))

  // Gather threads + messages
  const threadEntries = await Promise.all(
    options.threadIds.map(async (id) => {
      const thread = threadStore.getThreadById(id)
      if (!thread) return null
      const rawMessages = await fetchMessages(id)
      const messages = rawMessages
        .map((msg) => sanitizeMessage(msg as unknown as Record<string, unknown>))
        .filter((m): m is ExportableMessage => m !== null)
      return {
        thread: sanitizeThread(thread, messages.length),
        messages,
      }
    })
  )
  const validThreads = threadEntries.filter(
    (e): e is { thread: ExportableThread; messages: ExportableMessage[] } =>
      e !== null
  )

  // Collect model refs from threads
  const modelRefs = new Set<string>()
  for (const entry of validThreads) {
    if (entry.thread.model?.id) {
      modelRefs.add(entry.thread.model.id)
    }
  }

  // Build manifest
  const manifest: MobiusManifest = {
    version: 1,
    type:
      exportableAssistants.length > 0 && validThreads.length > 0
        ? 'bundle'
        : exportableAssistants.length > 0
          ? 'assistant'
          : validThreads.length > 0
            ? 'thread'
            : 'knowledge',
    name: options.name,
    description: options.description,
    createdAt: Date.now(),
    contents: {
      assistants: exportableAssistants.map((a) => a.id),
      threads: validThreads.map((t) => t.thread.id),
      knowledgeCollections: options.knowledgeCollections,
    },
    modelRefs: Array.from(modelRefs),
  }

  // Ask user where to save
  const outputPath = await save({
    defaultPath: `${options.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.mobius`,
    filters: [{ name: 'MOBIUS Package', extensions: ['mobius'] }],
  })

  if (!outputPath) return null

  // Invoke Rust to create the zip
  const result = await invoke<string>('create_mobius_package', {
    outputPath,
    manifest,
    assistants: exportableAssistants,
    threads: validThreads,
    knowledge: [], // Phase 1: knowledge export placeholder
  })

  return result
}

/** Quick-export a single assistant */
export async function exportAssistant(
  assistantId: string,
  includeInstructions = true
): Promise<string | null> {
  const assistant = useAssistant
    .getState()
    .assistants.find((a) => a.id === assistantId)
  if (!assistant) return null

  return exportMobiusPackage({
    name: assistant.name,
    description: assistant.description,
    assistantIds: [assistantId],
    threadIds: [],
    knowledgeCollections: [],
    includeInstructions,
  })
}

/** Quick-export a single thread */
export async function exportThread(
  threadId: string,
  includeInstructions = false
): Promise<string | null> {
  const thread = useThreads.getState().getThreadById(threadId)
  if (!thread) return null

  return exportMobiusPackage({
    name: thread.title || 'Thread Export',
    threadIds: [threadId],
    assistantIds: [],
    knowledgeCollections: [],
    includeInstructions,
  })
}

/** Quick-export selected threads */
export async function exportSelectedThreads(
  threadIds: string[],
  includeInstructions = false
): Promise<string | null> {
  return exportMobiusPackage({
    name: `MOBIUS Export ${new Date().toLocaleDateString()}`,
    threadIds,
    assistantIds: [],
    knowledgeCollections: [],
    includeInstructions,
  })
}

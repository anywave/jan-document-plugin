/**
 * Types for .mobius package sharing (export/import)
 */

/** Manifest at the root of every .mobius package */
type MobiusManifest = {
  version: 1
  type: 'assistant' | 'thread' | 'knowledge' | 'bundle'
  name: string
  description?: string
  createdAt: number
  createdBy?: string
  contents: {
    assistants: string[]
    threads: string[]
    knowledgeCollections: string[]
  }
  modelRefs: string[]
}

/** Sanitized assistant for export (no internal IDs leak) */
type ExportableAssistant = {
  id: string
  name: string
  avatar?: string
  description?: string
  instructions: string
  parameters: Record<string, unknown>
  created_at: number
}

/** Sanitized thread for export */
type ExportableThread = {
  id: string
  title: string
  updated: number
  model?: {
    id: string
    provider: string
  }
  assistantId?: string
  assistantName?: string
  messageCount: number
}

/** Sanitized message for export */
type ExportableMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: {
    type: string
    text?: { value: string; annotations: string[] }
  }[]
  created_at: number
  completed_at: number
}

/** Knowledge chunk for export */
type ExportableKnowledgeChunk = {
  id: string
  text: string
  metadata: Record<string, string | number | boolean>
  collection: string
}

/** What a .mobius package contains after reading */
type MobiusPackageContents = {
  manifest: MobiusManifest
  assistants: ExportableAssistant[]
  threads: {
    thread: ExportableThread
    messages: ExportableMessage[]
  }[]
  knowledge: ExportableKnowledgeChunk[]
}

/** Options for creating an export */
type MobiusExportOptions = {
  name: string
  description?: string
  assistantIds: string[]
  threadIds: string[]
  knowledgeCollections: string[]
  includeInstructions: boolean
}

/** Result of previewing a package before import */
type MobiusImportPreview = {
  manifest: MobiusManifest
  assistants: ExportableAssistant[]
  threads: ExportableThread[]
  knowledge: { collection: string; chunkCount: number }[]
  modelWarnings: string[]
}

/** Options for import — which items to actually bring in */
type MobiusImportOptions = {
  packagePath: string
  assistantIds: string[]
  threadIds: string[]
  knowledgeCollections: string[]
}

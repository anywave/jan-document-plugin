/**
 * Sanitization functions for .mobius package export.
 * Strips file paths, internal IDs, and sensitive metadata.
 */

/** Regex to match absolute file paths (Windows and Unix) */
const FILE_PATH_RE = /(?:[A-Z]:\\|\/(?:home|Users|tmp|var|etc)\/)[^\s"'<>|]+/gi

/** Strip absolute file paths from a string, replacing with basename */
export function stripFilePaths(text: string): string {
  return text.replace(FILE_PATH_RE, (match) => {
    const parts = match.replace(/\\/g, '/').split('/')
    return parts[parts.length - 1] || match
  })
}

/** Sanitize an assistant for export */
export function sanitizeAssistant(
  assistant: Assistant,
  includeInstructions: boolean
): ExportableAssistant {
  return {
    id: assistant.id,
    name: assistant.name,
    avatar: assistant.avatar,
    description: assistant.description
      ? stripFilePaths(assistant.description)
      : undefined,
    instructions: includeInstructions
      ? stripFilePaths(assistant.instructions)
      : '',
    parameters: { ...assistant.parameters },
    created_at: assistant.created_at,
  }
}

/** Sanitize a thread for export */
export function sanitizeThread(
  thread: Thread,
  messageCount: number
): ExportableThread {
  const assistantInfo = thread.assistants?.[0]
  return {
    id: thread.id,
    title: stripFilePaths(thread.title || 'Untitled'),
    updated: thread.updated,
    model: thread.model
      ? { id: thread.model.id, provider: thread.model.provider }
      : undefined,
    assistantId: assistantInfo?.id,
    assistantName: assistantInfo?.name,
    messageCount,
  }
}

/** Sanitize a message for export — strips tool_call_id, error_code, file attachments */
export function sanitizeMessage(
  msg: Record<string, unknown>
): ExportableMessage | null {
  const role = msg.role as string
  if (role === 'tool') return null

  const rawContent = msg.content as
    | { type: string; text?: { value: string; annotations: string[] }; image_url?: unknown }[]
    | undefined

  const content = (rawContent || [])
    .filter((c) => c.type === 'text' && c.text?.value)
    .map((c) => ({
      type: c.type,
      text: c.text
        ? {
            value: stripFilePaths(c.text.value),
            annotations: c.text.annotations || [],
          }
        : undefined,
    }))

  if (content.length === 0 && role !== 'system') return null

  return {
    id: (msg.id as string) || '',
    role: role as ExportableMessage['role'],
    content,
    created_at: (msg.created_at as number) || 0,
    completed_at: (msg.completed_at as number) || 0,
  }
}

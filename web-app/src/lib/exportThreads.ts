import { useThreads } from '@/hooks/useThreads'
import { fetchMessages } from '@/services/messages'
import type { ThreadMessage } from '@janhq/core'

type ExportFormat = 'clipboard' | 'text' | 'docx'

/** Extract plain text from a ThreadMessage's content array */
function messageText(msg: ThreadMessage): string {
  return (
    msg.content
      ?.map((c) => c.text?.value ?? '')
      .filter(Boolean)
      .join('\n') ?? ''
  )
}

/** Format a role label for export */
function roleLabel(role: string): string {
  switch (role) {
    case 'user':
      return 'User'
    case 'assistant':
      return 'Assistant'
    case 'system':
      return 'System'
    default:
      return role
  }
}

/** Format a single thread as plain text */
function formatThread(thread: Thread, messages: ThreadMessage[]): string {
  const date = new Date(thread.updated * 1000).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  const lines = [`=== ${thread.title || 'Untitled'} ===`, `Date: ${date}`, '']

  for (const msg of messages) {
    if (msg.role === 'system' || msg.role === 'tool') continue
    const text = messageText(msg)
    if (!text) continue
    lines.push(`[${roleLabel(msg.role)}]: ${text}`, '')
  }

  return lines.join('\n')
}

/** Trigger a browser download from a Blob */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/**
 * Export threads in the specified format.
 * - clipboard: copies formatted text to clipboard
 * - text: downloads a .txt file
 * - docx: downloads a .docx Word document
 */
export async function exportThreads(
  threadIds: string[],
  format: ExportFormat
): Promise<void> {
  const store = useThreads.getState()

  // Fetch all thread data + messages in parallel
  const entries = await Promise.all(
    threadIds.map(async (id) => {
      const thread = store.getThreadById(id)
      if (!thread) return null
      const messages = await fetchMessages(id)
      return { thread, messages }
    })
  )

  const valid = entries.filter(
    (e): e is { thread: Thread; messages: ThreadMessage[] } => e !== null
  )

  if (valid.length === 0) return

  if (format === 'clipboard' || format === 'text') {
    const text = valid.map((e) => formatThread(e.thread, e.messages)).join('\n\n---\n\n')

    if (format === 'clipboard') {
      await navigator.clipboard.writeText(text)
    } else {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const filename =
        valid.length === 1
          ? `${(valid[0].thread.title || 'thread').replace(/[^a-zA-Z0-9 ]/g, '')}.txt`
          : `exported-threads-${Date.now()}.txt`
      downloadBlob(blob, filename)
    }
  } else if (format === 'docx') {
    // Lazy-load docx to keep the main bundle slim
    const { Document, Packer, Paragraph, TextRun, HeadingLevel } = await import('docx')

    const sections = valid.map((e) => {
      const children: InstanceType<typeof Paragraph>[] = []

      // Thread title heading
      children.push(
        new Paragraph({
          text: e.thread.title || 'Untitled',
          heading: HeadingLevel.HEADING_1,
        })
      )

      // Date
      const date = new Date(e.thread.updated * 1000).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
      children.push(
        new Paragraph({
          children: [new TextRun({ text: `Date: ${date}`, italics: true, color: '666666' })],
        })
      )

      // Blank line
      children.push(new Paragraph({}))

      // Messages
      for (const msg of e.messages) {
        if (msg.role === 'system' || msg.role === 'tool') continue
        const text = messageText(msg)
        if (!text) continue

        children.push(
          new Paragraph({
            children: [
              new TextRun({ text: `[${roleLabel(msg.role)}]: `, bold: true }),
              new TextRun({ text }),
            ],
          })
        )
        children.push(new Paragraph({}))
      }

      return { children }
    })

    const doc = new Document({ sections })
    const buffer = await Packer.toBlob(doc)
    const filename =
      valid.length === 1
        ? `${(valid[0].thread.title || 'thread').replace(/[^a-zA-Z0-9 ]/g, '')}.docx`
        : `exported-threads-${Date.now()}.docx`
    downloadBlob(buffer, filename)
  }
}

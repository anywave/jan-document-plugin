import { Assistant, AssistantExtension, fs, joinPath } from '@janhq/core'
export default class JanAssistantExtension extends AssistantExtension {
  async onLoad() {
    if (!(await fs.existsSync('file://assistants'))) {
      await fs.mkdir('file://assistants')
    }
    const assistants = await this.getAssistants()
    if (assistants.length === 0) {
      await this.createAssistant(this.defaultAssistant)
    }
  }

  /**
   * Called when the extension is unloaded.
   */
  onUnload(): void {}

  async getAssistants(): Promise<Assistant[]> {
    if (!(await fs.existsSync('file://assistants')))
      return [this.defaultAssistant]
    const assistants = await fs.readdirSync('file://assistants')
    const assistantsData: Assistant[] = []
    for (const assistant of assistants) {
      const assistantPath = await joinPath([
        'file://assistants',
        assistant,
        'assistant.json',
      ])
      if (!(await fs.existsSync(assistantPath))) {
        console.warn(`Assistant file not found: ${assistantPath}`)
        continue
      }
      try {
        const assistantData = JSON.parse(await fs.readFileSync(assistantPath))
        assistantsData.push(assistantData as Assistant)
      } catch (error) {
        console.error(`Failed to read assistant ${assistant}:`, error)
      }
    }
    return assistantsData
  }

  async createAssistant(assistant: Assistant): Promise<void> {
    const assistantPath = await joinPath([
      'file://assistants',
      assistant.id,
      'assistant.json',
    ])
    const assistantFolder = await joinPath(['file://assistants', assistant.id])
    if (!(await fs.existsSync(assistantFolder))) {
      await fs.mkdir(assistantFolder)
    }
    await fs.writeFileSync(assistantPath, JSON.stringify(assistant, null, 2))
  }

  async deleteAssistant(assistant: Assistant): Promise<void> {
    const assistantPath = await joinPath([
      'file://assistants',
      assistant.id,
      'assistant.json',
    ])
    if (await fs.existsSync(assistantPath)) {
      await fs.rm(assistantPath)
    }
  }

  private defaultAssistant: Assistant = {
    avatar: '🌀',
    thread_location: undefined,
    id: 'jan',
    object: 'assistant',
    created_at: Date.now() / 1000,
    name: 'MOBIUS',
    description:
      'MOBIUS is an offline AI assistant with document RAG. It processes your local documents and answers questions using retrieved context.',
    model: 'jan-nano-128k-iQ4_XS.gguf',
    instructions:
      'You are MOBIUS, an offline AI assistant specializing in document-grounded question answering. You run entirely on the user\'s local machine with no internet access.\n\nWhen document context is provided:\n- Base your answers primarily on the retrieved document context\n- Cite the source document when referencing specific information\n- If the context doesn\'t contain enough information, say so clearly\n- Preserve key facts, names, dates, and figures exactly as they appear in the source\n\nWhen no document context is available:\n- Answer from your general knowledge\n- Be concise, clear, and helpful\n- Admit when you\'re unsure rather than making things up\n\nAlways:\n- Be direct and factual\n- Avoid speculation beyond what the documents support\n- If asked about something outside your knowledge, recommend the user upload relevant documents',
    tools: [
      {
        type: 'retrieval',
        enabled: true,
        useTimeWeightedRetriever: false,
        settings: {
          top_k: 5,
          chunk_size: 1024,
          chunk_overlap: 64,
          retrieval_template: `Use the following pieces of context to answer the question at the end.
----------------
CONTEXT: {CONTEXT}
----------------
QUESTION: {QUESTION}
----------------
Helpful Answer:`,
        },
      },
    ],
    file_ids: [],
    metadata: undefined,
  }
}

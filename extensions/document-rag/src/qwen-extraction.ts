/**
 * Qwen Extraction Service
 * Uses Qwen 2.5 7B Instruct to refine raw document chunks before sending to the chat model.
 * Falls back to raw chunks if Qwen is unavailable.
 */

const QWEN_MODEL_ID = 'qwen2.5-7b-instruct-q4_k_m'
const QWEN_GGUF_DIR = 'C:\\Users\\abc\\Documents\\Jan Stuff\\Models\\Qwen2.5-7B-Instruct-GGUF'
const QWEN_GGUF_FIRST_PART = 'qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf'

const EXTRACTION_SYSTEM_PROMPT = `You are a factual document extraction assistant. Your task is to summarize and consolidate the provided document chunks into a concise, accurate context for answering a user's question.

Rules:
- Extract only facts directly stated in the source chunks
- Preserve key facts, names, dates, numbers, and quotes exactly
- Do not add opinions, interpretations, or information not in the sources
- Organize the extracted information clearly
- If chunks contain contradictory information, note the contradiction
- Be concise — focus on information relevant to the user's question`

export interface ExtractionResult {
  refined_context: string
  source_chunks: string[]
  model_used: 'qwen' | 'raw'
}

/**
 * Check if Qwen model is available in llamacpp
 */
async function isQwenAvailable(): Promise<boolean> {
  try {
    const { fs, joinPath } = await import('@janhq/core')
    const modelYmlPath = await joinPath([
      'file://llamacpp',
      'models',
      QWEN_MODEL_ID,
      'model.yml',
    ])
    return await fs.existsSync(modelYmlPath)
  } catch {
    return false
  }
}

/**
 * Ensure Qwen model is registered in llamacpp/models/ by creating model.yml
 * if the GGUF files exist at the expected path.
 * This is idempotent — safe to call multiple times.
 */
export async function ensureQwenRegistered(): Promise<boolean> {
  try {
    const { fs, joinPath } = await import('@janhq/core')

    const modelDir = await joinPath([
      'file://llamacpp',
      'models',
      QWEN_MODEL_ID,
    ])
    const modelYmlPath = await joinPath([modelDir, 'model.yml'])

    // Already registered
    if (await fs.existsSync(modelYmlPath)) {
      return true
    }

    // Check if the GGUF source files exist on disk
    const ggufPath = `${QWEN_GGUF_DIR}\\${QWEN_GGUF_FIRST_PART}`
    // We can't easily check external paths via Jan's fs API, so we attempt registration
    // and let llamacpp validate at load time

    // Create the model directory
    if (!(await fs.existsSync(modelDir))) {
      await fs.mkdir(modelDir)
    }

    // Write model.yml pointing to the split GGUF
    // llamacpp handles split GGUFs automatically (reads -00001-of-NNNNN, loads all parts)
    const modelYml = `model_path: "${ggufPath.replace(/\\/g, '/')}"
name: "Qwen 2.5 7B Instruct (Q4_K_M) — Extraction"
size_bytes: 4731174912
ctx_len: 4096
ngl: 37
`
    await fs.writeFileSync(modelYmlPath, modelYml)

    console.log('[QwenExtraction] Registered Qwen model in llamacpp/models/')
    return true
  } catch (error) {
    console.warn('[QwenExtraction] Failed to register Qwen model:', error)
    return false
  }
}

/**
 * Send a completion request to Qwen via the local llamacpp server
 */
async function callQwenCompletion(
  systemPrompt: string,
  userPrompt: string
): Promise<string> {
  // Use the local OpenAI-compatible endpoint that llamacpp exposes
  const response = await fetch('http://127.0.0.1:1337/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: QWEN_MODEL_ID,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      temperature: 0.1,
      max_tokens: 512,
      stream: false,
    }),
  })

  if (!response.ok) {
    throw new Error(`Qwen completion failed: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  return data.choices?.[0]?.message?.content || ''
}

/**
 * Refine raw document chunks using Qwen extraction model.
 * Falls back to returning raw chunks if Qwen is not available.
 *
 * @param rawChunks - Array of raw text chunks from document retrieval
 * @param userQuery - The user's question to focus extraction on
 * @returns Extraction result with refined context or raw fallback
 */
export async function refineDocumentChunks(
  rawChunks: string[],
  userQuery: string
): Promise<ExtractionResult> {
  if (rawChunks.length === 0) {
    return {
      refined_context: '',
      source_chunks: [],
      model_used: 'raw',
    }
  }

  // Check if Qwen is available
  const available = await isQwenAvailable()
  if (!available) {
    return {
      refined_context: rawChunks.join('\n\n'),
      source_chunks: rawChunks,
      model_used: 'raw',
    }
  }

  try {
    const chunksText = rawChunks
      .map((chunk, i) => `[Chunk ${i + 1}]\n${chunk}`)
      .join('\n\n')

    const userPrompt = `User question: ${userQuery}\n\nDocument chunks:\n${chunksText}\n\nExtract and consolidate the relevant information from these chunks to help answer the user's question.`

    const refined = await callQwenCompletion(EXTRACTION_SYSTEM_PROMPT, userPrompt)

    if (refined.trim().length === 0) {
      // Empty response — fall back to raw
      return {
        refined_context: rawChunks.join('\n\n'),
        source_chunks: rawChunks,
        model_used: 'raw',
      }
    }

    return {
      refined_context: refined,
      source_chunks: rawChunks,
      model_used: 'qwen',
    }
  } catch (error) {
    console.warn('[QwenExtraction] Failed, falling back to raw chunks:', error)
    return {
      refined_context: rawChunks.join('\n\n'),
      source_chunks: rawChunks,
      model_used: 'raw',
    }
  }
}

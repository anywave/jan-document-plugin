import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { route } from '@/constants/routes'
import HeaderPage from '@/containers/HeaderPage'
import { ArrowLeft } from 'lucide-react'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute(route.docs as any)({
  component: Docs,
})

function Docs() {
  const navigate = useNavigate()

  return (
    <div className="flex h-full flex-col">
      <HeaderPage>
        <button
          onClick={() => navigate({ to: route.home })}
          className="flex items-center gap-2 hover:text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>User Manual</span>
        </button>
      </HeaderPage>
      <div className="h-full p-6 overflow-y-auto">
        <div className="max-w-2xl mx-auto space-y-8">

          <section>
            <h1 className="text-2xl font-bold mb-2">MOBIUS Chat Toolbar</h1>
            <p className="text-sm text-muted-fg">
              The toolbar below the chat input provides quick access to document
              processing, search, and model features. Hover over any icon to see
              its tooltip. Right-click for detailed information.
            </p>
          </section>

          {/* RAG Toggle */}
          <section id="rag-toggle" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Document RAG Toggle</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Controls whether your chat messages automatically search your indexed
              document library for relevant context before reaching the model.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 text-sm space-y-2">
              <p><strong>OFF (default):</strong> Messages go directly to the model
              with no document retrieval. This is the fastest mode.</p>
              <p><strong>ON:</strong> Each message queries ChromaDB for the top-15
              most relevant document chunks and injects them as context. This adds
              latency (depends on collection size) but enables document-grounded
              responses.</p>
              <p className="text-xs text-muted-fg/70 mt-2">
                Tip: Only enable RAG when you need to reference uploaded documents.
                Leave it OFF for general conversation.
              </p>
            </div>
          </section>

          {/* Smart Processing */}
          <section id="smart-processing" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Smart Processing</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Changes how uploaded documents are split into chunks for indexing.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 text-sm space-y-2">
              <p><strong>OFF (default):</strong> Fixed-size 500 character splits.
              Fast and predictable. Good for short documents and quick lookups.</p>
              <p><strong>ON:</strong> Structure-aware chunking that preserves
              headings, sections, and paragraph boundaries. Produces fewer but more
              meaningful chunks. Better for legal documents, research papers, and
              reports with clear structure.</p>
              <p className="text-xs text-muted-fg/70 mt-2">
                Tip: Enable Smart Processing for formal documents. Leave it OFF for
                plain text or notes.
              </p>
            </div>
          </section>

          {/* Upload Documents */}
          <section id="upload-documents" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Upload Documents</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Select one or more document files to process, chunk, embed, and store
              in your local ChromaDB collection.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 text-sm space-y-2">
              <p><strong>Supported formats:</strong> .txt, .md, .doc, .docx, .rtf</p>
              <p><strong>Single file:</strong> Processes immediately and generates
              a summary request in chat.</p>
              <p><strong>Multiple files:</strong> Batch-processed with a shared
              model instance. Progress shown via pill strip above the chat input.</p>
              <p><strong>Drag &amp; drop:</strong> You can also drag document files
              directly onto the chat window.</p>
            </div>
          </section>

          {/* Upload Folder */}
          <section id="upload-folder" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Upload Folder</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Scans an entire folder for supported document files and batch-processes
              all of them.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 text-sm space-y-2">
              <p>The scan is instant (done in Rust) and shows you how many files
              were found and how many were skipped. Processing then proceeds as a
              batch with real-time progress.</p>
            </div>
          </section>

          {/* Search Documents */}
          <section id="search-documents" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Search Documents</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Opens a search modal to query your indexed document collection. Results
              can be selected and added to the current chat context.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 text-sm space-y-2">
              <p>Uses semantic similarity search (not keyword matching) to find
              the most relevant chunks across all your indexed documents.</p>
            </div>
          </section>

          {/* Voice Input */}
          <section id="voice-input" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Voice Input</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Dictate your messages using your microphone. Speech is transcribed
              and appended to the chat input.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 text-sm space-y-2">
              <p><strong>Shortcut:</strong> Ctrl+M to toggle voice recording.</p>
              <p>Requires browser speech recognition support. Works best with
              clear audio and short phrases.</p>
            </div>
          </section>

          {/* Vision */}
          <section id="vision" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Vision</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Shown when the selected model supports image input. Allows you to
              attach images for the model to analyze.
            </p>
          </section>

          {/* Web Search */}
          <section id="web-search" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Web Search</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Shown when the selected model supports web search. Enables the model
              to fetch live information from the internet.
            </p>
          </section>

          {/* Reasoning */}
          <section id="reasoning" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">Reasoning</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Shown when the selected model supports chain-of-thought reasoning.
              The model will show its thinking process before answering.
            </p>
          </section>

          {/* Tools */}
          <section id="tools" className="scroll-mt-20 space-y-2 border-b border-border pb-6">
            <h2 className="text-lg font-semibold">MCP Tools</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Shown when MCP (Model Context Protocol) servers are connected and
              the model supports tool use. Click to see available tools and toggle
              them on/off.
            </p>
          </section>

          {/* Embeddings */}
          <section id="embeddings" className="scroll-mt-20 space-y-2 pb-6">
            <h2 className="text-lg font-semibold">Embeddings</h2>
            <p className="text-sm text-muted-fg leading-relaxed">
              Shown when the selected model supports embeddings generation. Used
              internally for document indexing and semantic search.
            </p>
          </section>

        </div>
      </div>
    </div>
  )
}

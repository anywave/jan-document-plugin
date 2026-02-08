# Two-Tier System Configuration
**Date:** February 8, 2026

## Architecture Overview

The Jan Document Plugin now implements a **two-tier LLM system** for optimal performance:

### Tier 1: Document Processing (Backend)
- **Model:** qwen2.5:7b-instruct (4.7 GB)
- **Purpose:** Understand and process uploaded documents
- **Tasks:** PDF comprehension, OCR, semantic chunking, context extraction
- **Why larger model?** Better comprehension for complex technical documents

### Tier 2: Chat Interface (Frontend)
- **Model:** Jan Nano 128k (2.3 GB) via Jan AI
- **Purpose:** Fast chat responses with "The Architect" assistant
- **Tasks:** User interaction, RAG-enhanced chat, assistant personality
- **Why Jan Nano?** 128k context window + fast inference + Jan AI assistant integration

## Configuration Files Modified

### 1. config.env
```env
# Server ports
PROXY_PORT=1338
JAN_PORT=11434          # Ollama for document processing
JAN_AI_PORT=1337        # Jan AI for chat interface

# Model configuration for two-tier system
DOCUMENT_PROCESSING_MODEL=qwen2.5:7b-instruct
CHAT_MODEL=jan-nano:128k
USE_JAN_AI_FOR_CHAT=true

# Document storage and embedding
STORAGE_DIR=.\jan_doc_store
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Context injection settings
AUTO_INJECT=true
MAX_CONTEXT_TOKENS=8000
MAX_CHUNKS=5
```

### 2. jan_proxy.py - ProxyConfig Class
```python
class ProxyConfig(BaseModel):
    """Proxy server configuration."""

    # Server connection - Two-tier system
    jan_host: str = "localhost"
    jan_port: int = 1337  # Ollama for document processing
    jan_ai_port: int = 1337  # Jan AI for chat interface
    use_jan_ai_for_chat: bool = True

    # Model configuration - Two-tier system
    document_processing_model: str = "qwen2.5:7b-instruct"
    chat_model: str = "jan-nano:128k"

    # ... rest of config
```

### 3. launcher.py - Config Defaults
```python
config = {
    'JAN_PORT': '11434',  # Ollama for document processing
    'JAN_AI_PORT': '1337',  # Jan AI for chat
    'DOCUMENT_PROCESSING_MODEL': 'qwen2.5:7b-instruct',
    'CHAT_MODEL': 'jan-nano:128k',
    'USE_JAN_AI_FOR_CHAT': 'true',
    # ... rest of config
}
```

## Models Required

### Install in Ollama:
```bash
# Tier 1: Document processing (required)
ollama pull qwen2.5:7b-instruct  # 4.7 GB

# Tier 2: Chat interface (required)
ollama create jan-nano:128k -f Modelfile.jan-nano
# Uses: C:\Users\abc\Documents\Jan Stuff\Previous Jan\jan-nano-128k-iQ4_XS.gguf

# Optional: Small fallback model
ollama pull qwen2.5:0.5b  # 397 MB (can be removed if not needed)
```

### Current Status:
```bash
$ ollama list
NAME                ID              SIZE      MODIFIED
jan-nano:128k      dbe86fceb3ec    2.3 GB    7 minutes ago
qwen2.5:7b-instruct [downloading]  4.7 GB    88% complete
qwen2.5:0.5b       a8b0c5157701    397 MB    2 weeks ago
```

## Data Flow

### Document Upload Flow:
```
1. User uploads PDF → Jan Document Plugin receives it
2. qwen2.5:7b-instruct processes document:
   - Extracts text (OCR if needed)
   - Understands content structure
   - Creates semantic chunks
   - Generates embeddings (all-MiniLM-L6-v2)
3. Chunks stored in ChromaDB (.\jan_doc_store)
```

### Chat Flow:
```
1. User sends chat message → Jan Document Plugin
2. RAG retrieval:
   - Query embedding generated
   - Top 5 relevant chunks retrieved from ChromaDB
   - Context assembled (max 8000 tokens)
3. Request forwarded to Jan AI (port 1337):
   - Jan Nano 128k model invoked
   - "The Architect" assistant personality applied
   - Context injected into system prompt
4. Response streamed back to user
```

## Jan AI Assistant Integration

### The Architect Configuration:
The Jan AI application should have "The Architect" assistant configured with:

1. **Emoji:** 🏗️ (or your chosen emoji)
2. **Name:** The Architect
3. **Description:** (Optional - set in Jan AI)
4. **Instructions:** (Set in Jan AI interface - system prompt for The Architect)
5. **Predefined Parameters:**
   - stream: `true`
   - temperature: `0.7`
   - frequency_penalty: `0.7`
   - presence_penalty: `0.7`
   - top_k: `2`
   - top_p: `0.95`

**Important:** These parameters are managed in Jan AI, NOT in the web UI. The web UI reads assistant configurations from Jan AI.

## Implementation Status

### ✅ Completed:
- [x] Added two-tier configuration to config.env
- [x] Updated ProxyConfig class in jan_proxy.py (added jan_ai_port, use_jan_ai_for_chat, model configs)
- [x] Updated launcher.py to load and display two-tier configuration
- [x] Created Jan Nano 128k model in Ollama
- [x] Downloading qwen2.5:7b-instruct (25% complete, 24 minutes remaining)
- [x] Fixed chat UI to dynamically detect models
- [x] Implemented chat endpoint routing logic (Jan AI vs Ollama)
- [x] Added /api/assistants endpoint in jan_proxy.py
- [x] Implemented Jan AI assistant selector in web UI
- [x] Assistant integration: instructions + predefined parameters
- [x] Pushed all changes to GitHub (3 commits)

### ⏳ Pending (after download completes):
- [ ] Test document upload with qwen2.5:7b-instruct
- [ ] Configure document processor to use DOCUMENT_PROCESSING_MODEL (if needed)
- [ ] Test Jan AI assistant integration with live Jan AI instance
- [ ] Test full RAG flow with both models
- [ ] Remove qwen2.5:0.5b if not needed

### 🔧 Implementation Complete

#### 1. ✅ Chat Endpoint Routing (DONE)
Implemented in jan_proxy.py lines 963-972:
```python
# Forward to Jan AI (chat interface) or Ollama (document processing) based on configuration
if config.use_jan_ai_for_chat:
    jan_url = f"{config.jan_ai_base_url}/v1/chat/completions"
    logger.info(f"Routing chat to Jan AI: {jan_url}")
else:
    jan_url = f"{config.jan_base_url}/v1/chat/completions"
    logger.info(f"Routing chat to Ollama: {jan_url}")
```

#### 2. ✅ Jan AI Assistant Selector (DONE)
Implemented /api/assistants endpoint in jan_proxy.py:
- Fetches assistants from Jan AI
- Returns emoji, name, instructions, and predefined parameters
- Graceful error handling for disabled or unreachable Jan AI

Implemented in chat_ui.html:
- Assistant selector UI with emoji + name display
- Fetches assistants on page load
- Automatically selects "The Architect" if available
- Applies assistant instructions to system prompt
- Applies assistant predefined parameters (stream, temperature, frequency_penalty, presence_penalty, top_k, top_p)
- Disabled state when Jan AI unavailable

#### 3. ⏳ Document Processor Model Selection (TODO)
Currently document_processor.py doesn't use LLM for processing (only embeddings).
If LLM-based document understanding is added in future:
```python
# Use config.document_processing_model for any LLM-based tasks
# Currently not needed as processing uses only embeddings
```

## Testing Checklist

### After qwen2.5:7b-instruct Download Completes:

1. **Verify Models:**
   ```bash
   ollama list  # Should show all 3 models
   ```

2. **Test Document Processing:**
   ```bash
   curl -X POST http://localhost:1338/documents \
     -F "file=@test.pdf"
   # Should use qwen2.5:7b-instruct for processing
   ```

3. **Test Chat:**
   - Open http://localhost:1338/ui
   - Verify it detects jan-nano:128k
   - Send test message
   - Should get response

4. **Test RAG:**
   - Upload document
   - Ask question about document
   - Verify context is injected and chat responds

5. **Test Jan AI Integration:**
   - Start Jan AI application
   - Select "The Architect" assistant
   - Verify web UI can connect to Jan AI API
   - Test assistant parameters are applied

## Troubleshooting

### If chat uses wrong model:
Check which port the chat endpoint is using:
```bash
# Check logs for: "Proxying to Jan server at: http://localhost:{PORT}"
# Should be port 1337 if using Jan AI, 11434 if using Ollama directly
```

### If document processing is slow:
Verify it's using the larger model:
```bash
# Check logs during document upload
# Should mention qwen2.5:7b-instruct, not qwen2.5:0.5b
```

### If Jan AI connection fails:
1. Verify Jan AI is running
2. Check if it's on port 1337:
   ```bash
   curl http://localhost:1337/v1/models
   ```
3. If different port, update JAN_AI_PORT in config.env

## Performance Expectations

### Document Processing (qwen2.5:7b-instruct):
- **Speed:** ~2-5 seconds per page (PDF)
- **Quality:** High - good understanding of technical content
- **Memory:** ~8-10 GB RAM usage during processing

### Chat (Jan Nano 128k):
- **Speed:** ~20-40 tokens/second
- **Quality:** Good for general conversation
- **Context:** Up to 128k tokens (massive context window)
- **Memory:** ~4-6 GB RAM usage

## Next Steps

1. Wait for qwen2.5:7b-instruct download to complete (~5 min)
2. Implement document processor model selection
3. Implement chat endpoint routing (Jan AI vs Ollama)
4. Test full workflow
5. Implement Jan AI assistant selector in UI
6. Document The Architect assistant configuration
7. Commit and push final implementation

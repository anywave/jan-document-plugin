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
- [x] Updated ProxyConfig class in jan_proxy.py
- [x] Updated launcher.py defaults
- [x] Created Jan Nano 128k model in Ollama
- [x] Downloading qwen2.5:7b-instruct (88% complete)
- [x] Fixed chat UI to dynamically detect models
- [x] Pushed all fixes to GitHub

### ⏳ Pending (after download completes):
- [ ] Test document upload with qwen2.5:7b-instruct
- [ ] Configure document processor to use DOCUMENT_PROCESSING_MODEL
- [ ] Test Jan AI assistant integration
- [ ] Implement Jan AI assistant selector in web UI
- [ ] Test full RAG flow with both models
- [ ] Remove qwen2.5:0.5b if not needed

### 🔧 TODO: Code Implementation

#### 1. Update document_processor.py
Need to modify document processing to use the configured larger model:
```python
# In document_processor.py, use config.document_processing_model
# for any LLM-based document understanding tasks
```

#### 2. Update chat endpoint
Need to route chat requests based on USE_JAN_AI_FOR_CHAT:
```python
# In jan_proxy.py chat_completions endpoint:
if config.use_jan_ai_for_chat:
    # Forward to Jan AI API (port jan_ai_port)
    jan_url = f"http://{config.jan_host}:{config.jan_ai_port}/v1/chat/completions"
else:
    # Forward to Ollama directly (port jan_port)
    jan_url = f"http://{config.jan_host}:{config.jan_port}/v1/chat/completions"
```

#### 3. Jan AI Assistant Selector (Web UI)
Need to add endpoint to fetch Jan AI assistants:
```python
@app.get("/api/assistants")
async def list_assistants():
    """Fetch assistants from Jan AI."""
    if config.use_jan_ai_for_chat:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://{config.jan_host}:{config.jan_ai_port}/v1/assistants")
                return resp.json()
        except:
            return {"assistants": []}
    return {"assistants": []}
```

Then update chat_ui.html to:
- Fetch and display assistants
- Show emoji + name in selector
- Apply assistant instructions and parameters to requests

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

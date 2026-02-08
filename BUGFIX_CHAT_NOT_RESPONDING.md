# BUG FIX: Chat Not Responding / Connection Error

## Issue Summary

**Symptom:** When users type a message in the chat UI, they get no response. The logs show `404 Not Found` errors when trying to reach Ollama's chat completions endpoint.

**Root Cause:** The chat UI has a hardcoded model name (`qwen2.5-7b-instruct`) that doesn't match the models available in Ollama. When the UI sends a chat request with this non-existent model name, Ollama returns 404.

## Detailed Analysis

### Error Log Pattern
```
INFO:     127.0.0.1:65088 - "POST /v1/chat/completions HTTP/1.1" 200 OK
[stderr] 2026-02-08 13:51:56,846 - jan-proxy - INFO - Streaming request to http://localhost:11434/v1/chat/completions with data: {
  "model": "qwen2.5-7b-instruct",  ← UI requests this model
  ...
}
[stderr] 2026-02-08 13:51:57,573 - httpx - INFO - HTTP Request: POST http://localhost:11434/v1/chat/completions "HTTP/1.1 404 Not Found"
[stderr] 2026-02-08 13:51:57,573 - jan-proxy - ERROR - Jan streaming error: 404
```

### Available vs Requested Model

| What Ollama Has | What UI Requests | Result |
|----------------|------------------|---------|
| `qwen2.5:0.5b` | `qwen2.5-7b-instruct` | 404 Error |

**Model Name Format Difference:**
- Ollama uses `:` separator: `qwen2.5:0.5b`, `qwen2.5:7b-instruct`
- UI was hardcoded with wrong format: `qwen2.5-7b-instruct` (missing colon)

### Code Location

**File:** `chat_ui.html`
**Line:** 434
```javascript
var MODEL = 'qwen2.5-7b-instruct';  // ← Hardcoded, non-existent model
```

## Solution

### Option 1: Quick Fix (Manual)
Users can manually edit `chat_ui.html` line 434 to match their Ollama model:
```javascript
var MODEL = 'qwen2.5:0.5b';  // Or whatever model they have installed
```

### Option 2: Proper Fix (Recommended)
Make the UI dynamically fetch and use available models. This requires:

1. **Fetch models on startup:**
```javascript
var MODEL = null;  // Start with null
var availableModels = [];

async function initializeModels() {
  try {
    const resp = await fetch(API + '/v1/models');
    const data = await resp.json();
    if (data.data && data.data.length > 0) {
      availableModels = data.data;
      MODEL = data.data[0].id;  // Use first available model
      updateModelDisplay();
    }
  } catch (err) {
    console.error('Failed to fetch models:', err);
    MODEL = 'qwen2.5:0.5b';  // Fallback
  }
}
```

2. **Call on page load:**
```javascript
window.addEventListener('DOMContentLoaded', function() {
  initializeModels();
  // ... other initialization
});
```

3. **Make model selector functional:**
Add click handler to `#model-select` to show a dropdown of available models.

### Option 3: Configuration File
Add a `DEFAULT_MODEL` setting to `config.env`:
```env
# Default LLM model to use in chat UI
DEFAULT_MODEL=qwen2.5:0.5b
```

Then modify `chat_ui.html` to read this from the server or inject it during template rendering.

## Prevention

### For Users (Documentation)

**Update `SETUP_REQUIREMENTS.md` to include:**
```markdown
## Required Ollama Models

The Jan Document Plugin requires at least one LLM model installed in Ollama.

### Recommended Models
- **Small/Fast (500MB-1GB):** `ollama pull qwen2.5:0.5b`
- **Balanced (4-5GB):** `ollama pull qwen2.5:7b-instruct`
- **Large (14-15GB):** `ollama pull qwen2.5:14b-instruct`

### Verify Installation
```bash
ollama list
```

Should show at least one model. Example output:
```
NAME                    ID              SIZE    MODIFIED
qwen2.5:0.5b           abcd1234        518MB   2 hours ago
```

### Configure Model
The UI will automatically detect and use the first available model. To use a specific model,
edit `chat_ui.html` line 434:
```javascript
var MODEL = 'your-model-name-here';  // e.g., 'qwen2.5:0.5b'
```
```

### For Developers (Code Quality)

**Add validation to prevent this:**

1. **Startup health check:**
```python
# In jan_proxy.py startup event
@app.on_event("startup")
async def verify_llm_available():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{config.jan_base_url}/v1/models")
            data = resp.json()
            if not data.get('data'):
                logger.error("No models available in Ollama!")
                logger.error("Run: ollama pull qwen2.5:0.5b")
    except Exception as e:
        logger.error(f"Cannot connect to Ollama: {e}")
```

2. **Model validation endpoint:**
```python
@app.get("/api/default-model")
async def get_default_model():
    """Return the first available model for UI to use."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{config.jan_base_url}/v1/models")
            data = resp.json()
            if data.get('data'):
                return {"model": data['data'][0]['id']}
    except:
        pass
    return {"model": "qwen2.5:0.5b"}  # Fallback
```

## Testing Checklist

After implementing the fix:

- [ ] Start Ollama: `ollama serve`
- [ ] Verify models exist: `ollama list`
- [ ] Start Jan Document Plugin: `py -3.12 launcher.py`
- [ ] Check startup logs for model detection
- [ ] Open UI: http://localhost:1338/ui
- [ ] Send test message: "Hello"
- [ ] Verify response appears (not just "...")
- [ ] Check logs show `200 OK` not `404 Not Found`

## Files Modified

- `chat_ui.html` - Line 434: Made MODEL dynamic
- `jan_proxy.py` - Added startup model verification
- `SETUP_REQUIREMENTS.md` - Added Ollama model installation instructions
- `README.md` - Added troubleshooting section

## Related Issues

This fix also resolves:
- "NetworkError when attempting to fetch resource"
- "Jan streaming error: 404"
- "Chat sends message but no response"
- Empty responses with loading spinner stuck

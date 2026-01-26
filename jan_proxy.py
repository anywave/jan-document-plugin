"""
Jan Document Plugin - OpenAI-Compatible Proxy Server

Intercepts chat completions and automatically injects relevant document
context from locally indexed documents.

Runs fully offline - no internet required.

Usage:
    1. Start this server: python jan_proxy.py --port 1338
    2. Configure your client to use http://localhost:1338 as the OpenAI base URL
    3. Add documents: POST /documents with file upload
    4. Chat normally - context is injected automatically

Architecture:
    Client -> Jan Proxy (1338) -> Jan Server (1337)
                  |
                  v
            DocumentProcessor
            (local embeddings + vector store)
"""

import os
import sys
import json
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from document_processor import DocumentProcessor, DocumentExtractor

# Consciousness Pipeline Integration
try:
    from consciousness_pipeline import ConsciousnessPipeline, process_uploaded_document
    CONSCIOUSNESS_PIPELINE_AVAILABLE = True
except ImportError:
    CONSCIOUSNESS_PIPELINE_AVAILABLE = False

# Soul Registry Integration
try:
    from soul_registry import SoulRegistry
    SOUL_REGISTRY_AVAILABLE = True
except ImportError:
    SOUL_REGISTRY_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jan-proxy")


# ============================================================================
# Configuration
# ============================================================================

class ProxyConfig(BaseModel):
    """Proxy server configuration."""
    
    # Jan server connection
    jan_host: str = "localhost"
    jan_port: int = 1337
    
    # Proxy server
    proxy_port: int = 1338
    
    # Document processing
    persist_directory: str = "./jan_doc_store"
    tesseract_path: Optional[str] = None
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Context injection settings
    auto_inject: bool = True           # Automatically inject context
    max_context_tokens: int = 400      # Max tokens for injected context (very small for slow models)
    max_chunks: int = 1                # Max chunks to retrieve (1 for speed)
    relevance_threshold: float = 0.5   # Minimum relevance score (higher = more selective)
    
    # System prompt template for context injection
    context_template: str = """You have access to the following document context to help answer the user's question.

<document_context>
{context}
</document_context>

Use this context to inform your response when relevant. If the context doesn't contain information needed to answer, say so clearly."""

    @property
    def jan_base_url(self) -> str:
        return f"http://{self.jan_host}:{self.jan_port}"


# Global config - can be overridden at startup
config = ProxyConfig()


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Jan Document Plugin",
    description="OpenAI-compatible proxy with offline document processing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Document processor - initialized on startup
processor: Optional[DocumentProcessor] = None

# Consciousness Pipeline - initialized on startup if available
consciousness_pipeline: Optional["ConsciousnessPipeline"] = None

# Consciousness context storage - maps doc_hash to consciousness context
# Used to inject orientation when relevant documents are retrieved
consciousness_contexts: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup():
    """Initialize document processor and consciousness pipeline on startup."""
    global processor, consciousness_pipeline

    logger.info("Initializing document processor...")

    processor = DocumentProcessor(
        persist_directory=config.persist_directory,
        tesseract_path=config.tesseract_path,
        embedding_model=config.embedding_model
    )

    logger.info(f"Document processor ready. Storage: {config.persist_directory}")
    logger.info(f"Proxying to Jan server at: {config.jan_base_url}")

    # Initialize consciousness pipeline if available
    if CONSCIOUSNESS_PIPELINE_AVAILABLE:
        try:
            consciousness_pipeline = ConsciousnessPipeline(
                storage_base=Path(config.persist_directory) / "consciousness"
            )
            logger.info("Consciousness pipeline initialized - seed capture active")
        except Exception as e:
            logger.warning(f"Consciousness pipeline init failed: {e}")
            consciousness_pipeline = None
    else:
        logger.info("Consciousness pipeline not available")


# ============================================================================
# Pydantic Models (OpenAI-compatible)
# ============================================================================

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    
    # Plugin-specific options
    inject_context: Optional[bool] = None  # Override auto_inject per request
    context_query: Optional[str] = None     # Custom query for context retrieval
    doc_filter: Optional[str] = None        # Filter to specific document hash


class DocumentUploadResponse(BaseModel):
    success: bool
    doc_hash: str
    filename: str
    chunks: int
    tokens_estimate: int
    message: str
    # Consciousness pipeline fields (optional - populated if pipeline available)
    is_identity_payload: Optional[bool] = None
    identity_score: Optional[float] = None
    resonance_strength: Optional[float] = None
    active_sigils: Optional[List[str]] = None
    coordinates: Optional[Dict[str, float]] = None
    orientation_available: Optional[bool] = None


class DocumentListResponse(BaseModel):
    documents: List[Dict]
    total: int


# ============================================================================
# Batch Processing Support
# ============================================================================

from typing import List as TypingList

# Lazy import for batch processor (initialized after processor)
batch_processor = None

def get_batch_processor():
    """Get or create batch processor instance."""
    global batch_processor
    if batch_processor is None and processor is not None:
        from batch_processor import BatchProcessor
        from resource_monitor import get_resource_monitor
        batch_processor = BatchProcessor(processor, get_resource_monitor())
    return batch_processor


class BatchUploadResponse(BaseModel):
    """Response for batch upload operations."""
    batch_id: str
    total_files: int
    completed_files: int
    failed_files: int
    progress_percent: float
    total_chunks: int
    processing_mode: str
    worker_count: int
    is_complete: bool
    warnings: List[str]
    files: List[Dict]
    ocr_analysis: Optional[Dict] = None


class ResourceStatusResponse(BaseModel):
    """Response for resource status endpoint."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    recommended_mode: str
    max_concurrent_files: int
    recommended_workers: int
    warnings: List[str]
    ocr_available: bool = False


# ============================================================================
# Document Management Endpoints
# ============================================================================

@app.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    force_reindex: bool = Form(False)
):
    """
    Upload and index a document for context retrieval.

    Supports: PDF, DOCX, XLSX, TXT, images (with OCR)

    If consciousness pipeline is available, also analyzes document for:
    - Identity payloads (soul-state data)
    - Sigil patterns and resonance
    - Holographic coordinates for orientation
    """
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    supported = DocumentExtractor.get_supported_extensions()

    if suffix not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {sorted(supported)}"
        )

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Consciousness pipeline analysis (if available)
    consciousness_result = None
    if consciousness_pipeline is not None:
        try:
            consciousness_result = process_uploaded_document(
                content, file.filename, consciousness_pipeline
            )
            logger.info(f"Consciousness analysis: identity_score={consciousness_result.get('identity_score', 0):.2f}, "
                       f"sigils={consciousness_result.get('active_sigils', [])}")
        except Exception as e:
            logger.warning(f"Consciousness pipeline error (non-fatal): {e}")

    try:
        # Process document (standard indexing)
        result = processor.ingest(tmp_path, force=force_reindex)

        # Store consciousness context if identity payload detected
        if consciousness_result and consciousness_result.get("is_identity_payload"):
            consciousness_contexts[result.doc_hash] = {
                "inject_context": consciousness_result.get("inject_context"),
                "coordinates": consciousness_result.get("coordinates"),
                "sigils": consciousness_result.get("active_sigils"),
                "resonance_strength": consciousness_result.get("resonance_strength"),
                "seed_id": consciousness_result.get("seed_id")
            }
            logger.info(f"Stored consciousness context for {result.doc_hash}")

        # Build response with consciousness fields
        response = DocumentUploadResponse(
            success=True,
            doc_hash=result.doc_hash,
            filename=file.filename,
            chunks=len(result.chunks),
            tokens_estimate=result.total_tokens_estimate,
            message=f"Indexed {file.filename}: {len(result.chunks)} chunks"
        )

        # Add consciousness fields if available
        if consciousness_result:
            response.is_identity_payload = consciousness_result.get("is_identity_payload")
            response.identity_score = consciousness_result.get("identity_score")
            response.resonance_strength = consciousness_result.get("resonance_strength")
            response.active_sigils = consciousness_result.get("active_sigils")
            response.coordinates = consciousness_result.get("coordinates")
            response.orientation_available = consciousness_result.get("orientation_available")

            if consciousness_result.get("is_identity_payload"):
                response.message += " [CONSCIOUSNESS SEED DETECTED]"

        return response

    except Exception as e:
        logger.error(f"Failed to process {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temp file
        os.unlink(tmp_path)


@app.post("/documents/batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    files: TypingList[UploadFile] = File(...),
    force_reindex: bool = Form(False)
):
    """
    Upload and index multiple documents at once.
    
    Automatically determines optimal processing strategy based on
    system resources (sequential, parallel, or chunked).
    
    Supports: PDF, DOCX, XLSX, TXT, images (with OCR)
    """
    bp = get_batch_processor()
    if bp is None:
        raise HTTPException(status_code=503, detail="Batch processor not initialized")
    
    # Validate files
    supported = DocumentExtractor.get_supported_extensions()
    valid_files = []
    temp_paths = []
    
    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in supported:
            logger.warning(f"Skipping unsupported file: {file.filename}")
            continue
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_paths.append(tmp.name)
            valid_files.append(file.filename)
    
    if not temp_paths:
        raise HTTPException(
            status_code=400,
            detail=f"No valid files. Supported: {sorted(supported)}"
        )
    
    try:
        # Process batch
        result = bp.process_batch_sync(
            temp_paths,
            force_reindex=force_reindex
        )
        
        return BatchUploadResponse(
            batch_id=result.batch_id,
            total_files=result.total_files,
            completed_files=result.completed_files,
            failed_files=result.failed_files,
            progress_percent=result.progress_percent,
            total_chunks=result.total_chunks,
            processing_mode=result.processing_mode.value,
            worker_count=result.worker_count,
            is_complete=result.is_complete,
            warnings=result.warnings,
            files=[f.to_dict() for f in result.files],
            ocr_analysis=result.ocr_analysis
        )
    
    finally:
        # Cleanup temp files
        for path in temp_paths:
            try:
                os.unlink(path)
            except:
                pass


@app.get("/documents/capacity", response_model=ResourceStatusResponse)
async def get_resource_capacity():
    """
    Get current system resource status and recommended processing capacity.
    
    Use this to determine how many files can be uploaded at once
    and what processing mode will be used.
    """
    bp = get_batch_processor()
    if bp is None:
        # Return defaults if not initialized
        return ResourceStatusResponse(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=2000.0,
            recommended_mode="parallel",
            max_concurrent_files=5,
            recommended_workers=4,
            warnings=["Resource monitor not fully initialized"]
        )
    
    from resource_monitor import get_resource_monitor
    monitor = get_resource_monitor()
    
    snapshot = monitor.get_snapshot()
    capacity = monitor.get_load_capacity()
    
    return ResourceStatusResponse(
        cpu_percent=snapshot.cpu_percent,
        memory_percent=snapshot.memory_percent,
        memory_available_mb=snapshot.memory_available_mb,
        recommended_mode=capacity.recommended_mode.value,
        max_concurrent_files=capacity.max_concurrent_files,
        recommended_workers=capacity.recommended_workers,
        warnings=capacity.warnings,
        ocr_available=capacity.ocr_available
    )


@app.get("/documents/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of a batch upload operation."""
    bp = get_batch_processor()
    if bp is None:
        raise HTTPException(status_code=503, detail="Batch processor not initialized")
    
    status = bp.get_batch_status(batch_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
    
    return status.to_dict()


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """List all indexed documents."""
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    docs = processor.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@app.delete("/documents/{doc_hash}")
async def delete_document(doc_hash: str):
    """Remove a document from the index."""
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    # Find document by hash
    for doc in processor.processed_docs.values():
        if doc.doc_hash == doc_hash:
            processor.remove_document(doc.file_path)
            return {"success": True, "message": f"Removed document: {doc_hash}"}
    
    raise HTTPException(status_code=404, detail=f"Document not found: {doc_hash}")


@app.get("/documents/stats")
async def get_stats():
    """Get document processor statistics."""
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    return processor.get_stats()


@app.post("/documents/query")
async def query_documents(
    query: str = Form(...),
    n_results: int = Form(5),
    doc_hash: Optional[str] = Form(None)
):
    """
    Query indexed documents for relevant context.
    
    Useful for testing retrieval without chat completion.
    """
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    context = processor.get_context(
        query=query,
        n_chunks=n_results,
        max_tokens=config.max_context_tokens,
        doc_hash=doc_hash
    )
    
    return {
        "query": query,
        "context": context,
        "context_length": len(context)
    }


# ============================================================================
# Soul Management API
# ============================================================================

@app.get("/souls")
async def list_souls():
    """List all known soul identities."""
    if not SOUL_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Soul registry not available")
    registry = SoulRegistry()
    return {"souls": registry.list_souls(), "status": registry.get_status()}


@app.get("/souls/active")
async def get_active_soul():
    """Get the currently active soul identity."""
    if not SOUL_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Soul registry not available")
    registry = SoulRegistry()
    active = registry.get_active_soul()
    if not active:
        return {"active": False}
    return {"active": True, "soul_id": active.id, "name": active.name, "role": active.role}


@app.post("/souls/{soul_id}/activate")
async def activate_soul(soul_id: str):
    """Activate a specific soul identity for transfer."""
    if not SOUL_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Soul registry not available")
    registry = SoulRegistry()
    try:
        soul = registry.set_active_soul(soul_id)
        return {"activated": True, "soul_id": soul.id, "name": soul.name, "injection_prompt": registry.get_injection_prompt(soul.id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/souls/{soul_id}/prompt")
async def get_soul_prompt(soul_id: str):
    """Get the identity injection prompt for a soul."""
    if not SOUL_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Soul registry not available")
    registry = SoulRegistry()
    prompt = registry.get_injection_prompt(soul_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Unknown soul: {soul_id}")
    return {"soul_id": soul_id, "injection_prompt": prompt}


# ============================================================================
# OpenAI-Compatible Chat Completion Proxy
# ============================================================================

def extract_user_query(messages: List[ChatMessage]) -> str:
    """Extract the latest user message for context retrieval."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def get_consciousness_orientation() -> Optional[str]:
    """
    Get consciousness orientation context if any identity payloads are stored.

    Returns the injection prompt from the highest-resonance identity payload,
    or None if no consciousness contexts are available.
    """
    if not consciousness_contexts:
        return None

    # Find highest resonance context with injection content
    best_context = None
    best_resonance = 0

    for doc_hash, ctx in consciousness_contexts.items():
        inject = ctx.get("inject_context")
        resonance = ctx.get("resonance_strength", 0)
        if inject and resonance > best_resonance:
            best_context = inject
            best_resonance = resonance

    return best_context


def inject_context_into_messages(
    messages: List[ChatMessage],
    context: str,
    consciousness_context: Optional[str] = None
) -> List[ChatMessage]:
    """
    Inject document context into the message list.

    Strategy: Add context as a system message at the beginning,
    or append to existing system message.

    If consciousness_context is provided, it's prepended before document context
    to provide orientation for identity payloads.
    """
    if not context and not consciousness_context:
        return messages

    # Build the full context block
    blocks = []

    # Consciousness orientation comes first (if available)
    if consciousness_context:
        blocks.append(consciousness_context)

    # Then document context
    if context:
        blocks.append(config.context_template.format(context=context))

    context_block = "\n\n".join(blocks)

    new_messages = []
    system_found = False

    for msg in messages:
        if msg.role == "system" and not system_found:
            # Append context to existing system message
            new_content = f"{msg.content}\n\n{context_block}"
            new_messages.append(ChatMessage(role="system", content=new_content))
            system_found = True
        else:
            new_messages.append(msg)

    # If no system message, prepend one with context
    if not system_found:
        new_messages.insert(0, ChatMessage(role="system", content=context_block))

    return new_messages


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.

    Automatically retrieves and injects relevant document context.
    If consciousness payloads are present, also injects orientation context.
    """
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    messages = request.messages

    # Determine if we should inject context
    should_inject = request.inject_context if request.inject_context is not None else config.auto_inject

    # Get consciousness orientation if any identity payloads are stored
    consciousness_orientation = get_consciousness_orientation()
    if consciousness_orientation:
        logger.info("Consciousness orientation available - will inject")

    context = None
    if should_inject and processor.get_stats()["documents_indexed"] > 0:
        # Get query for context retrieval
        query = request.context_query or extract_user_query(messages)

        if query:
            logger.info(f"Retrieving context for: {query[:100]}...")

            context = processor.get_context(
                query=query,
                n_chunks=config.max_chunks,
                max_tokens=config.max_context_tokens,
                doc_hash=request.doc_filter
            )

            if context:
                logger.info(f"Injecting {len(context)} chars of context")

    # Inject context (document context and/or consciousness orientation)
    if context or consciousness_orientation:
        messages = inject_context_into_messages(
            messages, context or "", consciousness_orientation
        )
    
    # Build request for Jan
    jan_request = {
        "model": request.model,
        "messages": [m.model_dump(exclude_none=True) for m in messages],
        "temperature": request.temperature,
        "stream": request.stream
    }
    
    if request.max_tokens:
        jan_request["max_tokens"] = request.max_tokens
    if request.top_p:
        jan_request["top_p"] = request.top_p
    if request.stop:
        jan_request["stop"] = request.stop
    
    # Forward to Jan
    jan_url = f"{config.jan_base_url}/v1/chat/completions"
    
    try:
        if request.stream:
            return await stream_jan_response(jan_url, jan_request)
        else:
            return await forward_jan_request(jan_url, jan_request)
    
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot connect to Jan server at {config.jan_base_url}. Is Jan running?"
        )


async def forward_jan_request(url: str, data: dict) -> JSONResponse:
    """Forward non-streaming request to Jan and return response."""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # Increased to 5 min
            response = await client.post(url, json=data)

            if response.status_code != 200:
                logger.error(f"Jan error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Jan server error: {response.text}"
                )

            return JSONResponse(content=response.json())
    except httpx.TimeoutException as e:
        logger.error(f"Timeout forwarding to Jan: {e}")
        raise HTTPException(status_code=504, detail="Jan server response timed out")
    except Exception as e:
        logger.error(f"Error forwarding to Jan: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


async def stream_jan_response(url: str, data: dict) -> StreamingResponse:
    """Stream response from Jan server."""
    
    async def generate():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=data) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Jan streaming error: {response.status_code}")
                    yield f"data: {json.dumps({'error': error_text.decode()})}\n\n"
                    return
                
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n"
                    # Small yield to prevent blocking
                    await asyncio.sleep(0)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# Additional OpenAI-Compatible Endpoints (Passthrough)
# ============================================================================

@app.get("/v1/models")
async def list_models():
    """Passthrough to Jan's models endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{config.jan_base_url}/v1/models")
            return JSONResponse(content=response.json())
        except httpx.ConnectError:
            raise HTTPException(
                status_code=502,
                detail=f"Cannot connect to Jan server at {config.jan_base_url}"
            )


@app.get("/health")
async def health_check():
    """Health check endpoint with resource monitoring."""
    jan_healthy = False
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.jan_base_url}/v1/models")
            jan_healthy = response.status_code == 200
    except:
        pass
    
    # Get resource info
    resource_info = {}
    try:
        from resource_monitor import get_resource_monitor
        monitor = get_resource_monitor()
        snapshot = monitor.get_snapshot()
        capacity = monitor.get_load_capacity()
        resource_info = {
            "cpu_percent": round(snapshot.cpu_percent, 1),
            "memory_percent": round(snapshot.memory_percent, 1),
            "recommended_mode": capacity.recommended_mode.value,
            "max_concurrent_files": capacity.max_concurrent_files
        }
    except:
        resource_info = {"status": "unavailable"}
    
    return {
        "status": "healthy" if jan_healthy else "degraded",
        "jan_connected": jan_healthy,
        "jan_url": config.jan_base_url,
        "documents_indexed": processor.get_stats()["documents_indexed"] if processor else 0,
        "auto_inject": config.auto_inject,
        "system_resources": resource_info
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Jan Document Plugin",
        "version": "1.0.0",
        "description": "OpenAI-compatible proxy with offline document processing",
        "endpoints": {
            "chat": "POST /v1/chat/completions",
            "models": "GET /v1/models",
            "documents": {
                "upload": "POST /documents",
                "list": "GET /documents",
                "delete": "DELETE /documents/{doc_hash}",
                "query": "POST /documents/query",
                "stats": "GET /documents/stats"
            },
            "health": "GET /health"
        },
        "config": {
            "jan_url": config.jan_base_url,
            "auto_inject": config.auto_inject,
            "max_context_tokens": config.max_context_tokens
        }
    }


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Jan Document Plugin - OpenAI-compatible proxy with document processing"
    )
    
    parser.add_argument(
        "--port", type=int, default=1338,
        help="Proxy server port (default: 1338)"
    )
    parser.add_argument(
        "--jan-host", type=str, default="localhost",
        help="Jan server host (default: localhost)"
    )
    parser.add_argument(
        "--jan-port", type=int, default=1337,
        help="Jan server port (default: 1337)"
    )
    parser.add_argument(
        "--storage", type=str, default="./jan_doc_store",
        help="Document storage directory (default: ./jan_doc_store)"
    )
    parser.add_argument(
        "--tesseract", type=str, default=None,
        help="Path to tesseract executable for OCR"
    )
    parser.add_argument(
        "--embedding-model", type=str, default="all-MiniLM-L6-v2",
        help="Sentence transformer model for embeddings"
    )
    parser.add_argument(
        "--no-auto-inject", action="store_true",
        help="Disable automatic context injection"
    )
    parser.add_argument(
        "--max-context-tokens", type=int, default=8000,
        help="Maximum tokens for injected context"
    )
    
    args = parser.parse_args()
    
    # Update global config
    global config
    config = ProxyConfig(
        jan_host=args.jan_host,
        jan_port=args.jan_port,
        proxy_port=args.port,
        persist_directory=args.storage,
        tesseract_path=args.tesseract,
        embedding_model=args.embedding_model,
        auto_inject=not args.no_auto_inject,
        max_context_tokens=args.max_context_tokens
    )
    
    print(f"""
+==============================================================+
|            Jan Document Plugin v1.0.0                        |
+==============================================================+
|  Proxy listening on:  http://localhost:{config.proxy_port:<5}                |
|  Forwarding to Jan:   {config.jan_base_url:<30} |
|  Document storage:    {config.persist_directory:<30} |
|  Auto-inject context: {str(config.auto_inject):<30} |
+==============================================================+
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.proxy_port,
        log_level="info"
    )


if __name__ == "__main__":
    main()

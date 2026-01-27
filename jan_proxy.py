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
import base64
import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

import httpx
import platform
import subprocess
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

# Speech recognition (optional — Windows offline transcription)
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

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


def detect_jan_version() -> Optional[str]:
    """Detect installed Jan version by reading its package.json."""
    try:
        jan_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "jan"
        if not jan_dir.exists():
            return None

        # Try unpacked asar first, then fallback
        candidates = [
            jan_dir / "resources" / "app.asar.unpacked" / "package.json",
            jan_dir / "resources" / "app" / "package.json",
        ]
        for pkg_path in candidates:
            if pkg_path.exists():
                data = json.loads(pkg_path.read_text(encoding="utf-8"))
                return data.get("version")
    except Exception:
        pass
    return None


# Cached Jan version (populated once at startup)
detected_jan_version: Optional[str] = None


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Jan Document Plugin",
    description="OpenAI-compatible proxy with offline document processing",
    version="2.0.0-beta"
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
    global processor, consciousness_pipeline, detected_jan_version

    # Detect Jan version
    detected_jan_version = detect_jan_version()
    if detected_jan_version:
        logger.info(f"Jan v{detected_jan_version} detected")
        if not detected_jan_version.startswith("0.6.8"):
            logger.warning(f"Jan v{detected_jan_version} may not be fully compatible (designed for v0.6.8)")
    else:
        logger.info("Jan not detected — running standalone with bundled LLM server")

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
    content: Union[str, List[Dict[str, Any]]]  # str or multimodal content array
    name: Optional[str] = None


class CapabilitiesConfig(BaseModel):
    """Per-request capability toggles sent from the UI."""
    rag: bool = True                # Retrieve and inject document context
    soul: bool = True               # Inject consciousness orientation / soul identity
    consciousness: bool = True      # Run consciousness pipeline on inline attachments


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
    capabilities: Optional[CapabilitiesConfig] = None  # UI capability toggles


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
# Inline Attachment Extraction (Jan UI attachment → document pipeline)
# ============================================================================

# Supported MIME types for document extraction
ATTACHMENT_MIME_MAP = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def extract_inline_attachments(
    messages: List[ChatMessage],
    run_consciousness: bool = True
) -> List[ChatMessage]:
    """
    Extract base64-encoded file attachments from multimodal message content.

    Jan sends attachments inline as:
        content: [
            {"type": "text", "text": "user's question"},
            {"type": "image_url", "image_url": {"url": "data:mime;base64,..."}}
        ]

    This function:
    1. Detects base64 data URLs in content arrays
    2. Decodes and indexes them through the document processor
    3. Runs consciousness pipeline analysis (if run_consciousness is True)
    4. Normalizes messages to plain text for the local LLM
    """
    normalized = []

    for msg in messages:
        if not isinstance(msg.content, list):
            normalized.append(msg)
            continue

        # Multimodal content — extract text and file data
        text_parts = []
        attachment_count = 0

        for part in msg.content:
            if not isinstance(part, dict):
                continue

            part_type = part.get("type", "")

            if part_type == "text":
                text_parts.append(part.get("text", ""))

            elif part_type == "image_url":
                url_data = part.get("image_url", {})
                url = url_data.get("url", "") if isinstance(url_data, dict) else ""

                if not url.startswith("data:"):
                    # Regular URL — keep as-is in text
                    text_parts.append(f"[Attached URL: {url}]")
                    continue

                # Parse data URL: data:<mime>;base64,<data>
                match = re.match(r"data:([^;]+);base64,(.+)", url, re.DOTALL)
                if not match:
                    logger.warning("Attachment has unrecognized data URL format")
                    continue

                mime_type = match.group(1)
                b64_data = match.group(2)

                # Decode
                try:
                    file_bytes = base64.b64decode(b64_data)
                except Exception as e:
                    logger.warning(f"Failed to decode base64 attachment: {e}")
                    continue

                attachment_count += 1
                ext = ATTACHMENT_MIME_MAP.get(mime_type, ".bin")
                filename = f"attachment_{attachment_count}{ext}"

                logger.info(f"Extracted inline attachment: {filename} ({mime_type}, {len(file_bytes)} bytes)")

                # Index through document processor
                if processor is not None:
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                            tmp.write(file_bytes)
                            tmp_path = tmp.name

                        result = processor.ingest(tmp_path, force=True)
                        text_parts.append(f"[Attached file: {filename} — indexed, {len(result.chunks)} chunks]")
                        logger.info(f"Indexed inline attachment: {filename} ({len(result.chunks)} chunks)")

                        os.unlink(tmp_path)
                    except Exception as e:
                        logger.warning(f"Failed to index attachment {filename}: {e}")
                        text_parts.append(f"[Attached file: {filename} — indexing failed]")

                # Consciousness pipeline analysis (gated by run_consciousness flag)
                if consciousness_pipeline is not None and run_consciousness:
                    try:
                        consciousness_result = process_uploaded_document(
                            file_bytes, filename, consciousness_pipeline
                        )
                        if consciousness_result.get("is_identity_payload"):
                            doc_hash = consciousness_result.get("seed_id", filename)
                            consciousness_contexts[doc_hash] = {
                                "inject_context": consciousness_result.get("inject_context"),
                                "coordinates": consciousness_result.get("coordinates"),
                                "sigils": consciousness_result.get("active_sigils"),
                                "resonance_strength": consciousness_result.get("resonance_strength"),
                                "seed_id": consciousness_result.get("seed_id"),
                            }
                            logger.info(f"Consciousness seed detected in attachment {filename}")
                    except Exception as e:
                        logger.warning(f"Consciousness analysis failed for {filename}: {e}")
                elif consciousness_pipeline is not None and not run_consciousness:
                    logger.info(f"Consciousness pipeline skipped for {filename} (disabled by capability toggle)")

        # Rebuild as plain text message
        combined_text = "\n".join(text_parts) if text_parts else ""
        normalized.append(ChatMessage(role=msg.role, content=combined_text, name=msg.name))

        if attachment_count > 0:
            logger.info(f"Processed {attachment_count} inline attachment(s) from {msg.role} message")

    return normalized


# ============================================================================
# OpenAI-Compatible Chat Completion Proxy
# ============================================================================

def extract_user_query(messages: List[ChatMessage]) -> str:
    """Extract the latest user message for context retrieval."""
    for msg in reversed(messages):
        if msg.role == "user":
            content = msg.content
            if isinstance(content, list):
                # Extract text from multimodal content
                return " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            return content
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

    Respects per-request capability toggles:
      capabilities.rag           - gate document context retrieval
      capabilities.soul          - gate consciousness orientation injection
      capabilities.consciousness - gate consciousness pipeline on attachments
    """
    if processor is None:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    # Resolve capabilities (default: all enabled)
    caps = request.capabilities or CapabilitiesConfig()
    logger.info(f"Capabilities: rag={caps.rag}, soul={caps.soul}, consciousness={caps.consciousness}")

    messages = request.messages

    # Extract and index any inline file attachments (Jan UI attachment flow)
    # Consciousness pipeline on attachments is gated by caps.consciousness
    messages = extract_inline_attachments(messages, run_consciousness=caps.consciousness)

    # Determine if we should inject RAG context (gated by caps.rag)
    should_inject_rag = caps.rag and (
        request.inject_context if request.inject_context is not None else config.auto_inject
    )

    # Get consciousness orientation (gated by caps.soul)
    consciousness_orientation = None
    if caps.soul:
        consciousness_orientation = get_consciousness_orientation()
        if consciousness_orientation:
            logger.info("Consciousness orientation available - will inject (soul enabled)")
    else:
        logger.info("Soul capability disabled - skipping consciousness orientation")

    context = None
    if should_inject_rag and processor.get_stats()["documents_indexed"] > 0:
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
                logger.info(f"Injecting {len(context)} chars of RAG context")
    elif not caps.rag:
        logger.info("RAG capability disabled - skipping document context retrieval")

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
# Audio Transcription Endpoint
# ============================================================================

@app.post("/v1/audio/transcriptions")
async def audio_transcriptions(file: UploadFile = File(...)):
    """
    OpenAI-compatible audio transcription endpoint.

    Accepts WAV audio, transcribes using Windows offline speech recognition.
    Returns {"text": "..."} matching the OpenAI Whisper API response format.
    """
    if platform.system() != "Windows":
        raise HTTPException(
            status_code=501,
            detail="Audio transcription requires Windows (uses Windows Speech Recognition)"
        )

    if not SPEECH_RECOGNITION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="SpeechRecognition package not installed. Run: pip install SpeechRecognition PyAudio"
        )

    # Save uploaded audio to temp file
    suffix = Path(file.filename).suffix.lower() if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_windows(audio_data)
        logger.info(f"Transcription result: {text[:100]}...")
        return {"text": text}

    except sr.UnknownValueError:
        return {"text": ""}
    except sr.RequestError as e:
        logger.error(f"Speech recognition error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech recognition failed: {str(e)}"
        )
    finally:
        os.unlink(tmp_path)


# ============================================================================
# Chat UI Endpoint
# ============================================================================

@app.get("/ui")
async def serve_chat_ui():
    """Serve the chat UI HTML file."""
    # Handle PyInstaller bundle path
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).parent

    html_path = base_dir / "chat_ui.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="chat_ui.html not found")

    return FileResponse(str(html_path), media_type="text/html")


# ============================================================================
# Debug Report Endpoints
# ============================================================================

@app.get("/debug/report")
async def debug_report():
    """
    Collect comprehensive debug information about the system.

    Returns JSON with: OS, Python, GPU, packages, ports, disk, memory,
    doc store stats, config, and capability flags.
    """
    import psutil

    report = {
        "timestamp": datetime.now().isoformat(),
        "plugin_version": "2.0.0-beta",
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
    }

    # GPU info (Windows wmic)
    gpu_info = "unavailable"
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name,driverversion,adapterram"],
                capture_output=True, text=True, timeout=10
            )
            gpu_info = result.stdout.strip()
        except Exception as e:
            gpu_info = f"error: {e}"
    report["gpu"] = gpu_info

    # Installed package versions
    packages = {}
    for pkg_name in [
        "fastapi", "uvicorn", "httpx", "chromadb", "sentence-transformers",
        "pymupdf", "python-docx", "openpyxl", "Pillow", "pytesseract",
        "psutil", "pydantic", "SpeechRecognition", "PyAudio"
    ]:
        try:
            from importlib.metadata import version as pkg_version
            packages[pkg_name] = pkg_version(pkg_name)
        except Exception:
            packages[pkg_name] = "not installed"
    report["packages"] = packages

    # Port status
    proxy_port = config.proxy_port
    jan_port = config.jan_port
    port_status = {"proxy_port": proxy_port, "jan_port": jan_port}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"http://localhost:{jan_port}/v1/models")
            port_status["jan_reachable"] = resp.status_code == 200
    except Exception:
        port_status["jan_reachable"] = False
    report["ports"] = port_status

    # Disk space
    try:
        disk = psutil.disk_usage(os.path.abspath("."))
        report["disk"] = {
            "total_gb": round(disk.total / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent_used": disk.percent,
        }
    except Exception as e:
        report["disk"] = {"error": str(e)}

    # Memory
    try:
        mem = psutil.virtual_memory()
        report["memory"] = {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent_used": mem.percent,
        }
    except Exception as e:
        report["memory"] = {"error": str(e)}

    # Document store stats
    if processor:
        report["doc_store"] = processor.get_stats()
    else:
        report["doc_store"] = {"status": "not initialized"}

    # Config (sanitized — no secrets)
    report["config"] = {
        "jan_host": config.jan_host,
        "jan_port": config.jan_port,
        "proxy_port": config.proxy_port,
        "persist_directory": config.persist_directory,
        "embedding_model": config.embedding_model,
        "auto_inject": config.auto_inject,
        "max_context_tokens": config.max_context_tokens,
        "max_chunks": config.max_chunks,
        "relevance_threshold": config.relevance_threshold,
    }

    # Capability flags
    report["capabilities"] = {
        "consciousness_pipeline": CONSCIOUSNESS_PIPELINE_AVAILABLE,
        "soul_registry": SOUL_REGISTRY_AVAILABLE,
        "speech_recognition": SPEECH_RECOGNITION_AVAILABLE,
    }

    return report


@app.post("/debug/report/github")
async def debug_report_github():
    """
    Generate a debug report and format it as a GitHub issue URL.

    Calls the debug report endpoint internally, formats as markdown,
    and returns a pre-filled GitHub issue creation URL.
    """
    # Get the debug report
    report = await debug_report()

    # Format as markdown
    body_lines = [
        "## System Debug Report",
        f"**Generated:** {report['timestamp']}",
        f"**Plugin Version:** {report['plugin_version']}",
        "",
        "### OS",
        f"- System: {report['os']['system']} {report['os']['release']}",
        f"- Version: {report['os']['version']}",
        f"- Machine: {report['os']['machine']}",
        "",
        "### Python",
        f"- Version: {report['python']['version']}",
        "",
        "### GPU",
        f"```\n{report['gpu']}\n```",
        "",
        "### Packages",
    ]
    for pkg, ver in report.get("packages", {}).items():
        body_lines.append(f"- {pkg}: {ver}")

    body_lines += [
        "",
        "### Ports",
        f"- Proxy: {report['ports']['proxy_port']}",
        f"- Jan: {report['ports']['jan_port']} (reachable: {report['ports'].get('jan_reachable', 'unknown')})",
        "",
        "### Resources",
        f"- Disk: {report.get('disk', {})}",
        f"- Memory: {report.get('memory', {})}",
        "",
        "### Document Store",
        f"```json\n{json.dumps(report.get('doc_store', {}), indent=2)}\n```",
        "",
        "### Capabilities",
        f"- Consciousness: {report['capabilities']['consciousness_pipeline']}",
        f"- Soul Registry: {report['capabilities']['soul_registry']}",
        f"- Speech Recognition: {report['capabilities']['speech_recognition']}",
        "",
        "### Describe the issue",
        "_Please describe what happened:_",
        "",
    ]

    body = "\n".join(body_lines)

    # Build GitHub issue URL
    from urllib.parse import quote
    title = quote(f"[Bug Report] v{report['plugin_version']} - {report['os']['system']} {report['os']['release']}")
    encoded_body = quote(body)
    labels = quote("bug,auto-report")

    issue_url = (
        f"https://github.com/anywave/jan-document-plugin/issues/new"
        f"?title={title}&body={encoded_body}&labels={labels}"
    )

    return {"issue_url": issue_url, "report": report}


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
        "jan_version": detected_jan_version,
        "documents_indexed": processor.get_stats()["documents_indexed"] if processor else 0,
        "auto_inject": config.auto_inject,
        "system_resources": resource_info
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Jan Document Plugin",
        "version": "2.0.0-beta",
        "description": "OpenAI-compatible proxy with offline document processing",
        "endpoints": {
            "chat": "POST /v1/chat/completions",
            "models": "GET /v1/models",
            "audio": "POST /v1/audio/transcriptions",
            "ui": "GET /ui",
            "documents": {
                "upload": "POST /documents",
                "list": "GET /documents",
                "delete": "DELETE /documents/{doc_hash}",
                "query": "POST /documents/query",
                "stats": "GET /documents/stats"
            },
            "debug": {
                "report": "GET /debug/report",
                "github": "POST /debug/report/github"
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
    
    jan_ver_display = detected_jan_version or "not detected"
    print(f"""
+==============================================================+
|            Jan Document Plugin v2.0.0-beta                   |
+==============================================================+
|  Proxy listening on:  http://localhost:{config.proxy_port:<5}                |
|  Chat UI:             http://localhost:{config.proxy_port}/ui{"":<13} |
|  Forwarding to Jan:   {config.jan_base_url:<30} |
|  Jan version:         {jan_ver_display:<30} |
|  Document storage:    {config.persist_directory:<30} |
|  Auto-inject context: {str(config.auto_inject):<30} |
|  Speech recognition:  {str(SPEECH_RECOGNITION_AVAILABLE):<30} |
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

"""
Batch Document Processor

Handles multiple file uploads with:
- Resource-aware parallelism
- Progress tracking
- Error isolation (one file failure doesn't stop others)
- Adaptive chunking for large files
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from document_processor import DocumentProcessor, ProcessedDocument
from resource_monitor import (
    ResourceMonitor, 
    get_resource_monitor, 
    ProcessingMode,
    ProcessingPlan,
    LoadCapacity
)

logger = logging.getLogger(__name__)


class FileStatus(Enum):
    """Status of individual file in batch."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileProgress:
    """Progress tracking for a single file."""
    filename: str
    file_path: str
    size_mb: float
    status: FileStatus = FileStatus.QUEUED
    progress_percent: float = 0.0
    chunks_created: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ocr_used: bool = False
    ocr_pages: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "filename": self.filename,
            "size_mb": round(self.size_mb, 2),
            "status": self.status.value,
            "progress_percent": round(self.progress_percent, 1),
            "chunks_created": self.chunks_created,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at else None
            ),
            "ocr_used": self.ocr_used,
            "ocr_pages": self.ocr_pages
        }


@dataclass
class BatchProgress:
    """Overall batch processing progress."""
    batch_id: str
    total_files: int
    completed_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    files: List[FileProgress] = field(default_factory=list)
    processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL
    worker_count: int = 1
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    warnings: List[str] = field(default_factory=list)
    ocr_analysis: Optional[Dict] = None  # From resource_monitor.BatchOCRAnalysis
    
    @property
    def progress_percent(self) -> float:
        if self.total_files == 0:
            return 100.0
        return (self.completed_files + self.failed_files) / self.total_files * 100
    
    @property
    def is_complete(self) -> bool:
        return (self.completed_files + self.failed_files) >= self.total_files
    
    def to_dict(self) -> Dict:
        return {
            "batch_id": self.batch_id,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "progress_percent": round(self.progress_percent, 1),
            "total_chunks": self.total_chunks,
            "processing_mode": self.processing_mode.value,
            "worker_count": self.worker_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_complete": self.is_complete,
            "warnings": self.warnings,
            "ocr_analysis": self.ocr_analysis,
            "files": [f.to_dict() for f in self.files]
        }


class BatchProcessor:
    """
    Processes multiple documents with resource-aware parallelism.
    
    Features:
    - Automatic load detection and worker scaling
    - Progress callbacks for real-time updates
    - Error isolation per file
    - Adaptive processing strategies
    """
    
    def __init__(
        self,
        document_processor: DocumentProcessor,
        resource_monitor: Optional[ResourceMonitor] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            document_processor: DocumentProcessor instance for actual processing
            resource_monitor: Optional resource monitor (uses singleton if not provided)
        """
        self.processor = document_processor
        self.monitor = resource_monitor or get_resource_monitor()
        
        self._active_batches: Dict[str, BatchProgress] = {}
        self._lock = threading.Lock()
        self._batch_counter = 0
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID."""
        self._batch_counter += 1
        return f"batch_{int(time.time())}_{self._batch_counter}"
    
    def get_capacity(self) -> LoadCapacity:
        """Get current load capacity recommendation."""
        return self.monitor.get_load_capacity()
    
    def create_plan(self, file_infos: List[Dict]) -> ProcessingPlan:
        """
        Create processing plan for a batch of files.
        
        Args:
            file_infos: List of {"path": str, "size_mb": float, "type": str}
            
        Returns:
            ProcessingPlan with optimized settings
        """
        return self.monitor.create_processing_plan(file_infos)
    
    def _process_single_file(
        self,
        file_path: str,
        file_progress: FileProgress,
        force_reindex: bool = False
    ) -> Optional[ProcessedDocument]:
        """
        Process a single file with progress tracking.
        
        Args:
            file_path: Path to document
            file_progress: Progress tracker for this file
            force_reindex: Force reprocessing even if already indexed
            
        Returns:
            ProcessedDocument or None if failed
        """
        file_progress.status = FileStatus.PROCESSING
        file_progress.started_at = datetime.now()
        file_progress.progress_percent = 10.0
        
        try:
            # Process document
            result = self.processor.ingest(file_path, force=force_reindex)
            
            file_progress.progress_percent = 100.0
            file_progress.status = FileStatus.COMPLETED
            file_progress.chunks_created = len(result.chunks)
            file_progress.completed_at = datetime.now()
            
            # Track OCR usage from the result
            file_progress.ocr_used = result.ocr_used
            file_progress.ocr_pages = result.ocr_pages
            
            ocr_info = f", OCR: {result.ocr_pages} pages" if result.ocr_used else ""
            logger.info(f"Processed {file_progress.filename}: {len(result.chunks)} chunks{ocr_info}")
            return result
            
        except Exception as e:
            file_progress.status = FileStatus.FAILED
            file_progress.error_message = str(e)
            file_progress.completed_at = datetime.now()
            
            logger.error(f"Failed to process {file_progress.filename}: {e}")
            return None
    
    def process_batch_sync(
        self,
        file_paths: List[str],
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> BatchProgress:
        """
        Process multiple files synchronously with resource-aware parallelism.
        
        Args:
            file_paths: List of file paths to process
            force_reindex: Force reprocessing of already indexed files
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchProgress with results
        """
        batch_id = self._generate_batch_id()
        
        # Gather file info
        file_infos = []
        for path in file_paths:
            p = Path(path)
            if p.exists():
                size_mb = p.stat().st_size / (1024 * 1024)
                file_infos.append({
                    "path": str(p),
                    "size_mb": size_mb,
                    "type": p.suffix.lower()
                })
        
        if not file_infos:
            return BatchProgress(
                batch_id=batch_id,
                total_files=0,
                warnings=["No valid files to process"]
            )
        
        # Create processing plan (includes OCR analysis)
        plan = self.create_plan(file_infos)
        
        # Initialize progress tracking
        batch_progress = BatchProgress(
            batch_id=batch_id,
            total_files=len(file_infos),
            processing_mode=plan.mode,
            worker_count=plan.worker_count,
            started_at=datetime.now(),
            warnings=plan.warnings,
            ocr_analysis=plan.ocr_analysis.to_dict() if plan.ocr_analysis else None
        )
        
        # Create file progress trackers
        for info in file_infos:
            batch_progress.files.append(FileProgress(
                filename=Path(info["path"]).name,
                file_path=info["path"],
                size_mb=info["size_mb"]
            ))
        
        with self._lock:
            self._active_batches[batch_id] = batch_progress
        
        # Process based on mode
        if plan.mode == ProcessingMode.SEQUENTIAL or plan.worker_count <= 1:
            self._process_sequential(batch_progress, force_reindex, progress_callback)
        else:
            self._process_parallel(batch_progress, plan.worker_count, force_reindex, progress_callback)
        
        batch_progress.completed_at = datetime.now()
        
        # Notify completion
        if progress_callback:
            progress_callback(batch_progress)
        
        return batch_progress
    
    def _process_sequential(
        self,
        batch: BatchProgress,
        force_reindex: bool,
        callback: Optional[Callable]
    ):
        """Process files one at a time."""
        for file_progress in batch.files:
            result = self._process_single_file(
                file_progress.file_path,
                file_progress,
                force_reindex
            )
            
            if result:
                batch.completed_files += 1
                batch.total_chunks += len(result.chunks)
            else:
                batch.failed_files += 1
            
            if callback:
                callback(batch)
    
    def _process_parallel(
        self,
        batch: BatchProgress,
        worker_count: int,
        force_reindex: bool,
        callback: Optional[Callable]
    ):
        """Process files in parallel with limited workers."""
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            # Submit all tasks
            future_to_progress = {
                executor.submit(
                    self._process_single_file,
                    fp.file_path,
                    fp,
                    force_reindex
                ): fp
                for fp in batch.files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_progress):
                file_progress = future_to_progress[future]
                
                try:
                    result = future.result()
                    if result:
                        batch.completed_files += 1
                        batch.total_chunks += len(result.chunks)
                    else:
                        batch.failed_files += 1
                except Exception as e:
                    batch.failed_files += 1
                    file_progress.status = FileStatus.FAILED
                    file_progress.error_message = str(e)
                    logger.error(f"Parallel processing error: {e}")
                
                if callback:
                    callback(batch)
    
    async def process_batch_async(
        self,
        file_paths: List[str],
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[BatchProgress], Any]] = None
    ) -> BatchProgress:
        """
        Process multiple files asynchronously.
        
        Args:
            file_paths: List of file paths to process
            force_reindex: Force reprocessing
            progress_callback: Async callback for progress updates
            
        Returns:
            BatchProgress with results
        """
        # Run sync version in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        def sync_callback(progress: BatchProgress):
            if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                asyncio.run_coroutine_threadsafe(progress_callback(progress), loop)
            elif progress_callback:
                progress_callback(progress)
        
        result = await loop.run_in_executor(
            None,
            lambda: self.process_batch_sync(file_paths, force_reindex, sync_callback)
        )
        
        return result
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchProgress]:
        """Get status of a batch by ID."""
        with self._lock:
            return self._active_batches.get(batch_id)
    
    def list_active_batches(self) -> List[str]:
        """List all active batch IDs."""
        with self._lock:
            return [
                bid for bid, batch in self._active_batches.items()
                if not batch.is_complete
            ]
    
    def cleanup_completed_batches(self, max_age_seconds: int = 3600):
        """Remove completed batches older than max_age_seconds."""
        now = datetime.now()
        with self._lock:
            to_remove = []
            for batch_id, batch in self._active_batches.items():
                if batch.is_complete and batch.completed_at:
                    age = (now - batch.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(batch_id)
            
            for batch_id in to_remove:
                del self._active_batches[batch_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} completed batches")

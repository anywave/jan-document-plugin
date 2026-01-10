"""
Resource Monitor for Jan Document Plugin

Monitors system resources and determines optimal processing strategy:
- Sequential: Low resources, process one file at a time
- Parallel: Adequate resources, process multiple files concurrently
- Chunked: Large files, split into smaller batches

Provides load capacity recommendations for batch uploads.
"""

import os
import sys
import logging
import threading
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing strategy based on available resources."""
    SEQUENTIAL = "sequential"      # One file at a time (low resources)
    PARALLEL = "parallel"          # Multiple files concurrently (normal)
    CHUNKED_PARALLEL = "chunked"   # Batch chunks with parallelism (large files)
    OCR_SEQUENTIAL = "ocr_sequential"  # OCR-heavy workload (CPU-bound)


class OCRRequirement(Enum):
    """OCR requirement level for a file."""
    NONE = "none"              # No OCR needed (text-based)
    LIKELY = "likely"          # Probably needs OCR (scanned PDF)
    REQUIRED = "required"      # Definitely needs OCR (image file)


@dataclass
class ResourceSnapshot:
    """Point-in-time resource usage snapshot."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_free_mb: float
    timestamp: float
    
    def to_dict(self) -> Dict:
        return {
            "cpu_percent": round(self.cpu_percent, 1),
            "memory_percent": round(self.memory_percent, 1),
            "memory_available_mb": round(self.memory_available_mb, 0),
            "disk_free_mb": round(self.disk_free_mb, 0),
            "timestamp": self.timestamp
        }


@dataclass
class LoadCapacity:
    """Recommended load capacity based on current resources."""
    max_concurrent_files: int
    max_file_size_mb: int
    recommended_mode: ProcessingMode
    recommended_workers: int
    warnings: List[str]
    ocr_available: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "max_concurrent_files": self.max_concurrent_files,
            "max_file_size_mb": self.max_file_size_mb,
            "recommended_mode": self.recommended_mode.value,
            "recommended_workers": self.recommended_workers,
            "warnings": self.warnings,
            "ocr_available": self.ocr_available
        }


@dataclass
class FileOCRAnalysis:
    """OCR analysis result for a single file."""
    path: str
    filename: str
    size_mb: float
    ocr_requirement: OCRRequirement
    estimated_ocr_pages: int = 0
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "filename": self.filename,
            "size_mb": round(self.size_mb, 2),
            "ocr_requirement": self.ocr_requirement.value,
            "estimated_ocr_pages": self.estimated_ocr_pages,
            "reason": self.reason
        }


@dataclass
class BatchOCRAnalysis:
    """OCR analysis for a batch of files."""
    total_files: int
    files_needing_ocr: int
    files_no_ocr: int
    estimated_ocr_pages: int
    ocr_percentage: float
    is_ocr_heavy: bool
    files: List[FileOCRAnalysis]
    recommendation: str
    
    def to_dict(self) -> Dict:
        return {
            "total_files": self.total_files,
            "files_needing_ocr": self.files_needing_ocr,
            "files_no_ocr": self.files_no_ocr,
            "estimated_ocr_pages": self.estimated_ocr_pages,
            "ocr_percentage": round(self.ocr_percentage, 1),
            "is_ocr_heavy": self.is_ocr_heavy,
            "recommendation": self.recommendation,
            "files": [f.to_dict() for f in self.files]
        }


@dataclass
class ProcessingPlan:
    """Execution plan for batch document processing."""
    mode: ProcessingMode
    worker_count: int
    batch_size: int
    estimated_time_seconds: float
    file_order: List[str]  # Optimized processing order
    warnings: List[str]
    ocr_analysis: Optional[BatchOCRAnalysis] = None


class ResourceMonitor:
    """
    Monitors system resources and provides processing recommendations.
    
    Thresholds are configurable to accommodate different hardware profiles.
    """
    
    # Default thresholds (can be overridden)
    DEFAULT_THRESHOLDS = {
        # CPU thresholds
        "cpu_low": 30,           # Below this = lots of headroom
        "cpu_medium": 60,        # Below this = normal operation
        "cpu_high": 80,          # Above this = constrained
        "cpu_critical": 95,      # Above this = avoid heavy work
        
        # Memory thresholds (percent)
        "memory_low": 40,
        "memory_medium": 65,
        "memory_high": 80,
        "memory_critical": 90,
        
        # Memory thresholds (absolute MB)
        "memory_min_available_mb": 500,    # Minimum free RAM
        "memory_comfortable_mb": 2000,     # Comfortable free RAM
        
        # Disk thresholds (MB)
        "disk_min_free_mb": 500,
        
        # Processing limits
        "max_workers": 8,                  # Maximum parallel workers
        "max_file_size_mb": 100,           # Max single file size
        "embedding_memory_per_chunk_mb": 2, # Estimated RAM per chunk during embedding
        
        # OCR thresholds
        "ocr_heavy_threshold": 0.3,        # >30% files need OCR = OCR-heavy batch
        "ocr_page_time_seconds": 2.0,      # Estimated seconds per OCR page
        "ocr_max_parallel_workers": 2,     # Max workers for OCR (CPU-bound)
        "scanned_pdf_text_threshold": 100, # Characters per page to consider "scanned"
    }
    
    # Image extensions that always require OCR
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
    
    # Text-based formats that never need OCR
    TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm'}
    
    def __init__(self, thresholds: Optional[Dict] = None):
        """
        Initialize resource monitor.
        
        Args:
            thresholds: Override default thresholds
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS}
        if thresholds:
            self.thresholds.update(thresholds)
        
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._history: List[ResourceSnapshot] = []
        self._history_max_size = 60  # Keep last 60 snapshots
        self._tesseract_available: Optional[bool] = None
        
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available - resource monitoring limited")
    
    def check_tesseract_available(self) -> bool:
        """Check if Tesseract OCR is available."""
        if self._tesseract_available is not None:
            return self._tesseract_available
        
        try:
            import pytesseract
            # Try to get version - will fail if not installed
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
            logger.info("Tesseract OCR is available")
        except Exception as e:
            self._tesseract_available = False
            logger.info(f"Tesseract OCR not available: {e}")
        
        return self._tesseract_available
    
    def analyze_file_ocr_requirement(self, file_path: str) -> FileOCRAnalysis:
        """
        Analyze a single file to determine OCR requirements.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileOCRAnalysis with OCR requirement details
        """
        from pathlib import Path
        
        p = Path(file_path)
        suffix = p.suffix.lower()
        size_mb = p.stat().st_size / (1024 * 1024) if p.exists() else 0
        
        # Image files always need OCR
        if suffix in self.IMAGE_EXTENSIONS:
            return FileOCRAnalysis(
                path=file_path,
                filename=p.name,
                size_mb=size_mb,
                ocr_requirement=OCRRequirement.REQUIRED,
                estimated_ocr_pages=1,  # Images = 1 page
                reason="Image file - OCR required"
            )
        
        # Text-based files never need OCR
        if suffix in self.TEXT_EXTENSIONS:
            return FileOCRAnalysis(
                path=file_path,
                filename=p.name,
                size_mb=size_mb,
                ocr_requirement=OCRRequirement.NONE,
                estimated_ocr_pages=0,
                reason="Text-based format"
            )
        
        # DOCX/XLSX are text-based
        if suffix in {'.docx', '.xlsx', '.xls', '.doc'}:
            return FileOCRAnalysis(
                path=file_path,
                filename=p.name,
                size_mb=size_mb,
                ocr_requirement=OCRRequirement.NONE,
                estimated_ocr_pages=0,
                reason="Office document with embedded text"
            )
        
        # PDF - need to check if scanned
        if suffix == '.pdf':
            return self._analyze_pdf_ocr(file_path, p.name, size_mb)
        
        # Unknown - assume might need OCR
        return FileOCRAnalysis(
            path=file_path,
            filename=p.name,
            size_mb=size_mb,
            ocr_requirement=OCRRequirement.LIKELY,
            estimated_ocr_pages=max(1, int(size_mb * 10)),  # Rough estimate
            reason="Unknown format - may need OCR"
        )
    
    def _analyze_pdf_ocr(self, file_path: str, filename: str, size_mb: float) -> FileOCRAnalysis:
        """
        Analyze a PDF to determine if it's scanned (needs OCR).
        
        Uses quick sampling to avoid reading entire large PDFs.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            # Can't check - assume likely needs OCR for safety
            estimated_pages = max(1, int(size_mb * 5))  # ~5 pages per MB typical
            return FileOCRAnalysis(
                path=file_path,
                filename=filename,
                size_mb=size_mb,
                ocr_requirement=OCRRequirement.LIKELY,
                estimated_ocr_pages=estimated_pages,
                reason="Cannot analyze PDF (PyMuPDF not available)"
            )
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # Sample pages: first, middle, last (max 5 samples)
            sample_indices = [0]
            if total_pages > 2:
                sample_indices.append(total_pages // 2)
            if total_pages > 1:
                sample_indices.append(total_pages - 1)
            
            scanned_count = 0
            text_threshold = self.thresholds["scanned_pdf_text_threshold"]
            
            for idx in sample_indices:
                if idx < total_pages:
                    page = doc[idx]
                    text = page.get_text().strip()
                    if len(text) < text_threshold:
                        scanned_count += 1
            
            doc.close()
            
            # Determine OCR requirement based on samples
            scanned_ratio = scanned_count / len(sample_indices) if sample_indices else 0
            
            if scanned_ratio > 0.5:
                # More than half of sampled pages are scanned
                return FileOCRAnalysis(
                    path=file_path,
                    filename=filename,
                    size_mb=size_mb,
                    ocr_requirement=OCRRequirement.REQUIRED,
                    estimated_ocr_pages=total_pages,
                    reason=f"Scanned PDF detected ({scanned_count}/{len(sample_indices)} sampled pages lack text)"
                )
            elif scanned_ratio > 0:
                # Some pages might be scanned
                estimated_ocr = int(total_pages * scanned_ratio)
                return FileOCRAnalysis(
                    path=file_path,
                    filename=filename,
                    size_mb=size_mb,
                    ocr_requirement=OCRRequirement.LIKELY,
                    estimated_ocr_pages=estimated_ocr,
                    reason=f"Mixed PDF - some pages may need OCR ({estimated_ocr} of {total_pages})"
                )
            else:
                # Text-based PDF
                return FileOCRAnalysis(
                    path=file_path,
                    filename=filename,
                    size_mb=size_mb,
                    ocr_requirement=OCRRequirement.NONE,
                    estimated_ocr_pages=0,
                    reason=f"Text-based PDF ({total_pages} pages)"
                )
                
        except Exception as e:
            # Error analyzing - assume might need OCR
            logger.warning(f"Error analyzing PDF {filename}: {e}")
            estimated_pages = max(1, int(size_mb * 5))
            return FileOCRAnalysis(
                path=file_path,
                filename=filename,
                size_mb=size_mb,
                ocr_requirement=OCRRequirement.LIKELY,
                estimated_ocr_pages=estimated_pages,
                reason=f"Error analyzing PDF: {str(e)[:50]}"
            )
    
    def analyze_batch_ocr(self, file_paths: List[str]) -> BatchOCRAnalysis:
        """
        Analyze a batch of files for OCR requirements.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            BatchOCRAnalysis with aggregate OCR info
        """
        analyses = [self.analyze_file_ocr_requirement(fp) for fp in file_paths]
        
        files_needing_ocr = sum(
            1 for a in analyses 
            if a.ocr_requirement in (OCRRequirement.REQUIRED, OCRRequirement.LIKELY)
        )
        files_no_ocr = len(analyses) - files_needing_ocr
        total_ocr_pages = sum(a.estimated_ocr_pages for a in analyses)
        
        ocr_percentage = (files_needing_ocr / len(analyses) * 100) if analyses else 0
        is_ocr_heavy = ocr_percentage > (self.thresholds["ocr_heavy_threshold"] * 100)
        
        # Generate recommendation
        if not self.check_tesseract_available():
            if files_needing_ocr > 0:
                recommendation = (
                    f"⚠️ {files_needing_ocr} file(s) may need OCR but Tesseract is not installed. "
                    "Install Tesseract for best results."
                )
            else:
                recommendation = "All files can be processed without OCR."
        elif is_ocr_heavy:
            estimated_time = total_ocr_pages * self.thresholds["ocr_page_time_seconds"]
            recommendation = (
                f"OCR-heavy batch: {files_needing_ocr} files ({total_ocr_pages} pages) need OCR. "
                f"Estimated OCR time: {estimated_time/60:.1f} minutes. "
                "Using sequential processing to manage CPU load."
            )
        elif files_needing_ocr > 0:
            recommendation = (
                f"{files_needing_ocr} file(s) need OCR. "
                "Mixed batch - will use limited parallelism."
            )
        else:
            recommendation = "No OCR needed - full parallel processing available."
        
        return BatchOCRAnalysis(
            total_files=len(analyses),
            files_needing_ocr=files_needing_ocr,
            files_no_ocr=files_no_ocr,
            estimated_ocr_pages=total_ocr_pages,
            ocr_percentage=ocr_percentage,
            is_ocr_heavy=is_ocr_heavy,
            files=analyses,
            recommendation=recommendation
        )
    
    def get_snapshot(self) -> ResourceSnapshot:
        """Get current resource usage snapshot."""
        if not PSUTIL_AVAILABLE:
            # Return conservative estimates without psutil
            return ResourceSnapshot(
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_available_mb=2000.0,
                disk_free_mb=10000.0,
                timestamp=time.time()
            )
        
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return ResourceSnapshot(
            cpu_percent=cpu,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            disk_free_mb=disk.free / (1024 * 1024),
            timestamp=time.time()
        )
    
    def get_load_capacity(self) -> LoadCapacity:
        """
        Determine current load capacity based on resources.
        
        Returns recommended limits for batch processing.
        """
        snapshot = self.get_snapshot()
        warnings = []
        
        # Check OCR availability
        ocr_available = self.check_tesseract_available()
        
        # Determine CPU-based capacity
        if snapshot.cpu_percent >= self.thresholds["cpu_critical"]:
            cpu_workers = 1
            warnings.append("CPU critically high - sequential processing only")
        elif snapshot.cpu_percent >= self.thresholds["cpu_high"]:
            cpu_workers = 2
            warnings.append("CPU usage high - limiting parallelism")
        elif snapshot.cpu_percent >= self.thresholds["cpu_medium"]:
            cpu_workers = 4
        else:
            cpu_workers = self.thresholds["max_workers"]
        
        # Determine memory-based capacity
        if snapshot.memory_percent >= self.thresholds["memory_critical"]:
            mem_workers = 1
            mem_files = 1
            warnings.append("Memory critically low - sequential processing only")
        elif snapshot.memory_percent >= self.thresholds["memory_high"]:
            mem_workers = 2
            mem_files = 3
            warnings.append("Memory usage high - limiting batch size")
        elif snapshot.memory_available_mb < self.thresholds["memory_min_available_mb"]:
            mem_workers = 1
            mem_files = 2
            warnings.append(f"Low available memory ({snapshot.memory_available_mb:.0f}MB)")
        elif snapshot.memory_available_mb < self.thresholds["memory_comfortable_mb"]:
            mem_workers = 3
            mem_files = 5
        else:
            mem_workers = self.thresholds["max_workers"]
            mem_files = 20
        
        # Disk space check
        if snapshot.disk_free_mb < self.thresholds["disk_min_free_mb"]:
            warnings.append(f"Low disk space ({snapshot.disk_free_mb:.0f}MB free)")
            max_file_size = 10  # Limit file sizes
        else:
            max_file_size = self.thresholds["max_file_size_mb"]
        
        # Combine constraints (use minimum)
        recommended_workers = min(cpu_workers, mem_workers)
        max_concurrent = min(cpu_workers, mem_files)
        
        # Determine processing mode
        if recommended_workers <= 1:
            mode = ProcessingMode.SEQUENTIAL
        elif recommended_workers <= 2:
            mode = ProcessingMode.PARALLEL
        else:
            mode = ProcessingMode.PARALLEL
        
        return LoadCapacity(
            max_concurrent_files=max_concurrent,
            max_file_size_mb=max_file_size,
            recommended_mode=mode,
            recommended_workers=recommended_workers,
            warnings=warnings,
            ocr_available=ocr_available
        )
    
    def estimate_processing_time(
        self,
        file_sizes_mb: List[float],
        chunk_estimates: List[int]
    ) -> float:
        """
        Estimate total processing time for a batch of files.
        
        Args:
            file_sizes_mb: List of file sizes in MB
            chunk_estimates: Estimated chunks per file
            
        Returns:
            Estimated seconds to complete
        """
        capacity = self.get_load_capacity()
        
        # Base time estimates (seconds)
        EXTRACTION_MB_PER_SEC = 5.0       # PDF/DOCX extraction speed
        EMBEDDING_CHUNKS_PER_SEC = 10.0   # Embedding generation speed
        
        total_extraction_time = sum(file_sizes_mb) / EXTRACTION_MB_PER_SEC
        total_embedding_time = sum(chunk_estimates) / EMBEDDING_CHUNKS_PER_SEC
        
        # Adjust for parallelism
        effective_workers = capacity.recommended_workers
        parallel_factor = 1.0 / effective_workers
        
        # Add overhead for coordination
        overhead = len(file_sizes_mb) * 0.5  # 0.5s per file overhead
        
        estimated = (total_extraction_time + total_embedding_time) * parallel_factor + overhead
        
        return max(estimated, 1.0)  # Minimum 1 second
    
    def create_processing_plan(
        self,
        files: List[Dict]  # [{"path": str, "size_mb": float, "type": str}]
    ) -> ProcessingPlan:
        """
        Create an optimized processing plan for batch files.
        
        Factors in:
        - Current system resources
        - OCR requirements (CPU-bound)
        - File sizes and types
        
        Args:
            files: List of file info dicts with path, size_mb, type
            
        Returns:
            ProcessingPlan with optimized order and settings
        """
        capacity = self.get_load_capacity()
        warnings = list(capacity.warnings)
        
        # Analyze OCR requirements
        file_paths = [f["path"] for f in files]
        ocr_analysis = self.analyze_batch_ocr(file_paths)
        
        # Add OCR warnings
        if not capacity.ocr_available and ocr_analysis.files_needing_ocr > 0:
            warnings.append(
                f"Tesseract not installed - {ocr_analysis.files_needing_ocr} file(s) "
                "with images/scanned content may not be fully processed"
            )
        
        # Adjust workers based on OCR load
        if ocr_analysis.is_ocr_heavy:
            # OCR is CPU-bound and single-threaded per page
            # Limit parallelism to avoid CPU thrashing
            ocr_max_workers = self.thresholds["ocr_max_parallel_workers"]
            adjusted_workers = min(capacity.recommended_workers, ocr_max_workers)
            
            if adjusted_workers < capacity.recommended_workers:
                warnings.append(
                    f"OCR-heavy batch - reducing workers from {capacity.recommended_workers} "
                    f"to {adjusted_workers} to manage CPU load"
                )
            
            mode = ProcessingMode.OCR_SEQUENTIAL if adjusted_workers <= 1 else ProcessingMode.PARALLEL
        else:
            adjusted_workers = capacity.recommended_workers
            mode = capacity.recommended_mode
        
        # Sort files: prioritize non-OCR files first for faster initial results
        # Then smaller OCR files before larger ones
        def sort_key(f):
            analysis = next(
                (a for a in ocr_analysis.files if a.path == f["path"]), 
                None
            )
            if analysis:
                ocr_priority = 0 if analysis.ocr_requirement == OCRRequirement.NONE else 1
                return (ocr_priority, analysis.estimated_ocr_pages, f["size_mb"])
            return (0, 0, f["size_mb"])
        
        sorted_files = sorted(files, key=sort_key)
        
        # Check for oversized files
        oversized = [f for f in files if f["size_mb"] > capacity.max_file_size_mb]
        if oversized:
            warnings.append(
                f"{len(oversized)} file(s) exceed recommended size limit "
                f"({capacity.max_file_size_mb}MB) - processing may be slow"
            )
        
        # Calculate timing with OCR factored in
        file_sizes = [f["size_mb"] for f in sorted_files]
        chunk_estimates = [
            max(1, int(f["size_mb"] * 1024 * 0.1 / 4))
            for f in sorted_files
        ]
        
        # Base time estimate
        estimated_time = self.estimate_processing_time(file_sizes, chunk_estimates)
        
        # Add OCR time
        if ocr_analysis.estimated_ocr_pages > 0:
            ocr_time = (
                ocr_analysis.estimated_ocr_pages * 
                self.thresholds["ocr_page_time_seconds"]
            )
            # OCR parallelism factor
            ocr_time = ocr_time / max(1, adjusted_workers)
            estimated_time += ocr_time
        
        # Determine batch size based on capacity and OCR
        if mode in (ProcessingMode.SEQUENTIAL, ProcessingMode.OCR_SEQUENTIAL):
            batch_size = 1
        else:
            batch_size = min(capacity.max_concurrent_files, len(files))
        
        return ProcessingPlan(
            mode=mode,
            worker_count=adjusted_workers,
            batch_size=batch_size,
            estimated_time_seconds=estimated_time,
            file_order=[f["path"] for f in sorted_files],
            warnings=warnings,
            ocr_analysis=ocr_analysis
        )
    
    def start_background_monitoring(self, interval_seconds: float = 1.0):
        """Start background resource monitoring thread."""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor_loop():
            while self._monitoring:
                try:
                    snapshot = self.get_snapshot()
                    self._history.append(snapshot)
                    
                    # Trim history
                    if len(self._history) > self._history_max_size:
                        self._history = self._history[-self._history_max_size:]
                    
                except Exception as e:
                    logger.error(f"Resource monitoring error: {e}")
                
                time.sleep(interval_seconds)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Background resource monitoring started")
    
    def stop_background_monitoring(self):
        """Stop background monitoring thread."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info("Background resource monitoring stopped")
    
    def get_history(self, last_n: int = 10) -> List[ResourceSnapshot]:
        """Get recent resource history."""
        return self._history[-last_n:]
    
    def get_average_usage(self, last_n: int = 10) -> Dict:
        """Get average resource usage over recent history."""
        history = self.get_history(last_n)
        
        if not history:
            snapshot = self.get_snapshot()
            return {
                "cpu_percent_avg": snapshot.cpu_percent,
                "memory_percent_avg": snapshot.memory_percent,
                "samples": 1
            }
        
        return {
            "cpu_percent_avg": sum(s.cpu_percent for s in history) / len(history),
            "memory_percent_avg": sum(s.memory_percent for s in history) / len(history),
            "samples": len(history)
        }


# Singleton instance
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """Get or create the singleton resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor

"""
Jan Document Plugin

Offline document processing for Jan.AI local LLMs.
"""

__version__ = "1.0.0"
__author__ = "Anywave Creations"

from .document_processor import (
    DocumentProcessor,
    DocumentExtractor,
    SemanticChunker,
    LocalVectorStore,
    DocumentType,
    DocumentChunk,
    ProcessedDocument
)

__all__ = [
    "DocumentProcessor",
    "DocumentExtractor", 
    "SemanticChunker",
    "LocalVectorStore",
    "DocumentType",
    "DocumentChunk",
    "ProcessedDocument"
]

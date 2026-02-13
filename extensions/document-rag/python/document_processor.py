#!/usr/bin/env python3
"""
Document Processor for AVACHATTER
Main orchestrator for document processing pipeline.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
import time


def emit_progress(step: int, total_steps: int, step_name: str, detail: str = "",
                   file_path: str = "", batch_index: int = -1, batch_total: int = -1):
    """Write a progress JSON line to stderr for the Rust bridge to pick up."""
    progress = {
        "progress": True,
        "step": step,
        "total_steps": total_steps,
        "step_name": step_name,
        "detail": detail,
        "file": file_path,
        "percent": int((step / total_steps) * 100) if total_steps > 0 else 0,
    }
    if batch_index >= 0:
        progress["batch_index"] = batch_index
        progress["batch_total"] = batch_total
    print(json.dumps(progress), file=sys.stderr, flush=True)


def emit_file_result(file_path: str, success: bool, chunks_created: int,
                     error: Optional[str], processing_time: float,
                     batch_index: int, batch_total: int):
    """Emit a per-file result on stderr so Rust can forward immediately."""
    result = {
        "file_result": True,
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "success": success,
        "chunks_created": chunks_created,
        "error": error,
        "processing_time": round(processing_time, 1),
        "batch_index": batch_index,
        "batch_total": batch_total,
    }
    print(json.dumps(result), file=sys.stderr, flush=True)

# Import all processors
from pdf_processor import PDFProcessor
from docx_processor import DOCXProcessor
from image_processor import ImageProcessor
from embedder import Embedder
from vector_store import VectorStore


class DocumentProcessor:
    """Main document processing pipeline."""

    def __init__(
        self,
        vector_db_path: str = "./chroma_db",
        tesseract_path: Optional[str] = None
    ):
        """
        Initialize document processor.

        Args:
            vector_db_path: Path to ChromaDB persistence directory
            tesseract_path: Path to Tesseract executable (Windows)
        """
        self.pdf_processor = PDFProcessor(tesseract_path)
        self.docx_processor = DOCXProcessor()
        self.image_processor = ImageProcessor(tesseract_path)
        self.embedder = Embedder()
        self.vector_store = VectorStore(vector_db_path)

        self.supported_extensions = {
            '.txt': 'text',
            '.md': 'text',
            '.doc': 'docx',
            '.docx': 'docx',
            '.rtf': 'text',
        }

    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type from extension.

        Args:
            file_path: Path to file

        Returns:
            File type ('pdf', 'docx', 'text', 'image', 'unknown')
        """
        ext = Path(file_path).suffix.lower()
        return self.supported_extensions.get(ext, 'unknown')

    def extract_text_from_file(
        self,
        file_path: str,
        use_ocr: bool = True,
        password: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Extract text from any supported file type.

        Args:
            file_path: Path to file
            use_ocr: Whether to use OCR for PDFs/images
            password: Password for encrypted PDFs

        Returns:
            Dictionary with:
                - text: Extracted text
                - file_type: Detected file type
                - metadata: File metadata
                - error: Error message if failed
        """
        result = {
            'text': '',
            'file_type': '',
            'metadata': {},
            'error': None
        }

        try:
            file_type = self.detect_file_type(file_path)
            result['file_type'] = file_type

            if file_type == 'pdf':
                pdf_result = self.pdf_processor.extract_text(
                    file_path,
                    use_ocr=use_ocr,
                    password=password
                )
                result['text'] = pdf_result['text']
                result['metadata'] = pdf_result['metadata']
                result['error'] = pdf_result['error']

            elif file_type == 'docx':
                docx_result = self.docx_processor.extract_text(file_path)
                result['text'] = docx_result['text']
                result['metadata'] = docx_result['metadata']
                result['error'] = docx_result['error']

            elif file_type == 'text':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    result['text'] = f.read()

            elif file_type == 'image':
                if use_ocr:
                    img_result = self.image_processor.extract_text(file_path)
                    result['text'] = img_result['text']
                    result['metadata'] = {
                        'size': img_result['size'],
                        'format': img_result['format'],
                        'confidence': img_result['confidence']
                    }
                    result['error'] = img_result['error']
                else:
                    result['error'] = "OCR disabled for image files"

            else:
                result['error'] = f"Unsupported file type: {file_type}"

            # Add common metadata
            if not result['error']:
                result['metadata']['file_name'] = os.path.basename(file_path)
                result['metadata']['file_size'] = os.path.getsize(file_path)
                result['metadata']['processed_at'] = datetime.now().isoformat()

        except Exception as e:
            result['error'] = str(e)

        return result

    def process_and_index_document(
        self,
        file_path: str,
        collection_name: str = "documents",
        chunk_size: int = 500,
        overlap: int = 50,
        use_ocr: bool = True,
        password: Optional[str] = None,
        smart: bool = False
    ) -> Dict[str, any]:
        """
        Complete processing pipeline: extract, chunk, embed, store.

        Args:
            file_path: Path to document
            collection_name: Vector store collection name
            chunk_size: Text chunk size
            overlap: Chunk overlap
            use_ocr: Use OCR for scanned content
            password: Password for encrypted PDFs

        Returns:
            Dictionary with processing results
        """
        result = {
            'success': False,
            'file_path': file_path,
            'chunks_created': 0,
            'error': None
        }

        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_size_mb = file_size / (1024 * 1024)
            start_time = time.time()

            # Estimate expected chunks (rough: ~500 chars/chunk, text files ~1 byte/char)
            est_chunks = max(1, file_size // 450)

            # Step 1: Extract text
            emit_progress(1, 4, "Extracting text",
                          f"{file_name} ({file_size_mb:.1f} MB) — est. ~{est_chunks} chunks",
                          file_path)
            extract_result = self.extract_text_from_file(
                file_path,
                use_ocr=use_ocr,
                password=password
            )

            if extract_result['error']:
                result['error'] = f"Extraction failed: {extract_result['error']}"
                return result

            if not extract_result['text'].strip():
                result['error'] = "No text extracted from document"
                return result

            text_len = len(extract_result['text'])
            elapsed = time.time() - start_time

            # Step 2: Chunk and embed
            est_chunks_from_text = max(1, text_len // 450)
            emit_progress(2, 4, "Chunking & embedding",
                          f"{text_len:,} chars extracted in {elapsed:.1f}s — chunking into ~{est_chunks_from_text} pieces & embedding...",
                          file_path)
            doc_result = self.embedder.embed_document(
                extract_result['text'],
                chunk_size=chunk_size,
                overlap=overlap,
                metadata=extract_result['metadata'],
                smart=smart
            )

            if doc_result['error']:
                result['error'] = f"Embedding failed: {doc_result['error']}"
                return result

            result['chunks_created'] = len(doc_result['chunks'])
            num_chunks = len(doc_result['chunks'])
            elapsed = time.time() - start_time

            # Step 3: Prepare for storage
            emit_progress(3, 4, "Preparing storage",
                          f"{num_chunks} chunks, {len(doc_result['embeddings'])} embeddings ({elapsed:.1f}s elapsed)",
                          file_path)

            # Create unique IDs
            file_id = Path(file_path).stem
            doc_ids = [f"{file_id}_chunk_{i}" for i in range(num_chunks)]

            # Prepare documents and metadata
            documents = [chunk['text'] for chunk in doc_result['chunks']]
            metadatas = []
            for i, chunk in enumerate(doc_result['chunks']):
                meta = dict(doc_result['metadata'])
                meta['chunk_index'] = i
                meta['chunk_start'] = chunk['start']
                meta['chunk_end'] = chunk['end']
                metadatas.append(meta)

            # Step 4: Store in vector database
            emit_progress(4, 4, "Storing in ChromaDB",
                          f"Writing {num_chunks} chunks to collection '{collection_name}'...",
                          file_path)
            store_result = self.vector_store.add_documents(
                documents=documents,
                embeddings=doc_result['embeddings'],
                metadatas=metadatas,
                ids=doc_ids,
                collection_name=collection_name
            )

            if store_result['error']:
                result['error'] = f"Storage failed: {store_result['error']}"
                return result

            total_time = time.time() - start_time
            result['success'] = True
            result['processing_time'] = round(total_time, 1)

            # Build document summary for the frontend
            full_text = extract_result['text']
            words = full_text.split()
            word_count = len(words)

            # Detect sections by looking for heading-like lines
            lines = full_text.split('\n')
            sections = []
            for line in lines:
                stripped = line.strip()
                # Heuristic: short lines in ALL CAPS or ending with colon are likely headings
                if stripped and len(stripped) < 120:
                    if stripped.isupper() and len(stripped) > 3:
                        sections.append(stripped)
                    elif stripped.endswith(':') and len(stripped) < 80:
                        sections.append(stripped.rstrip(':'))
            # Deduplicate and limit
            seen = set()
            unique_sections = []
            for s in sections:
                key = s.lower()
                if key not in seen:
                    seen.add(key)
                    unique_sections.append(s)
            sections = unique_sections[:20]

            # Text preview (first ~500 chars)
            preview = full_text[:500].strip()
            if len(full_text) > 500:
                preview += '...'

            result['document_summary'] = {
                'file_name': file_name,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size_mb, 2),
                'word_count': word_count,
                'char_count': text_len,
                'chunks_created': num_chunks,
                'sections_detected': sections,
                'preview': preview,
                'processing_time': round(total_time, 1),
            }

        except Exception as e:
            result['error'] = str(e)

        return result

    def process_batch(
        self,
        file_paths: List[str],
        collection_name: str = "documents",
        chunk_size: int = 500,
        overlap: int = 50,
        use_ocr: bool = True,
        smart: bool = False,
    ) -> Dict[str, any]:
        """
        Process multiple files in a single batch. Model is loaded ONCE.

        Emits per-file progress on stderr with batch_index/batch_total.
        Emits file_result JSON on stderr after each file completes.
        Returns aggregate result on stdout.
        """
        batch_total = len(file_paths)
        results = []
        success_count = 0
        error_count = 0
        batch_start = time.time()

        for idx, file_path in enumerate(file_paths):
            file_start = time.time()
            file_name = os.path.basename(file_path)

            emit_progress(1, 4, "Extracting text",
                          f"[{idx+1}/{batch_total}] {file_name}",
                          file_path, batch_index=idx, batch_total=batch_total)

            try:
                result = self.process_and_index_document(
                    file_path=file_path,
                    collection_name=collection_name,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    use_ocr=use_ocr,
                    smart=smart,
                )
            except Exception as e:
                result = {
                    'success': False,
                    'file_path': file_path,
                    'chunks_created': 0,
                    'error': str(e),
                    'processing_time': round(time.time() - file_start, 1),
                }

            file_time = time.time() - file_start
            if 'processing_time' not in result or result.get('processing_time') is None:
                result['processing_time'] = round(file_time, 1)

            if result.get('success'):
                success_count += 1
            else:
                error_count += 1

            results.append(result)

            # Emit per-file result on stderr for real-time Rust forwarding
            emit_file_result(
                file_path=file_path,
                success=result.get('success', False),
                chunks_created=result.get('chunks_created', 0),
                error=result.get('error'),
                processing_time=result.get('processing_time', file_time),
                batch_index=idx,
                batch_total=batch_total,
            )

        total_time = round(time.time() - batch_start, 1)

        return {
            'results': results,
            'success_count': success_count,
            'error_count': error_count,
            'total_files': batch_total,
            'total_time': total_time,
        }

    def query_documents(
        self,
        query: str,
        collection_name: str = "documents",
        top_k: int = 5
    ) -> Dict[str, any]:
        """
        Query indexed documents.

        Args:
            query: Search query
            collection_name: Collection to search
            top_k: Number of results

        Returns:
            Dictionary with query results
        """
        result = {
            'query': query,
            'results': [],
            'error': None
        }

        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_text(query)

            # Query vector store
            query_result = self.vector_store.query_documents(
                query_embedding=query_embedding,
                n_results=top_k,
                collection_name=collection_name
            )

            if query_result['error']:
                result['error'] = query_result['error']
                return result

            # Format results
            for i in range(len(query_result['ids'])):
                result['results'].append({
                    'id': query_result['ids'][i],
                    'text': query_result['documents'][i],
                    'metadata': query_result['metadatas'][i],
                    'distance': query_result['distances'][i]
                })

        except Exception as e:
            result['error'] = str(e)

        return result

    def get_collection_stats(self, collection_name: str = "documents") -> Dict[str, any]:
        """
        Get statistics about a collection.

        Args:
            collection_name: Collection name

        Returns:
            Dictionary with stats
        """
        return {
            'collection': collection_name,
            'document_count': self.vector_store.get_collection_count(collection_name),
            'all_collections': self.vector_store.list_collections()
        }

    def check_health(self, collection_name: str = "documents", auto_recover: bool = False) -> Dict[str, any]:
        """
        Check ChromaDB health status.

        Args:
            collection_name: Collection to check
            auto_recover: If True, delete and recreate corrupt chroma_db dir

        Returns:
            Dictionary with health status
        """
        result = {
            'healthy': False,
            'document_count': 0,
            'error': None,
            'recovered': False,
        }

        try:
            count = self.vector_store.get_collection_count(collection_name)
            result['healthy'] = True
            result['document_count'] = count
        except Exception as e:
            result['error'] = str(e)

            if auto_recover:
                try:
                    import shutil
                    db_path = self.vector_store.persist_directory
                    if os.path.exists(db_path):
                        shutil.rmtree(db_path)
                        os.makedirs(db_path, exist_ok=True)
                    # Reinitialize vector store
                    self.vector_store = VectorStore(db_path)
                    result['recovered'] = True
                    result['healthy'] = True
                    result['error'] = None
                except Exception as recover_err:
                    result['error'] = f"Recovery failed: {recover_err}"

        return result

    def list_by_source(self, collection_name: str = "documents") -> Dict[str, any]:
        """
        List all document chunks grouped by their source file.

        Args:
            collection_name: Collection name

        Returns:
            Dictionary with documents grouped by file_name metadata
        """
        result = {
            'documents': [],
            'error': None,
        }

        try:
            collection = self.vector_store.get_or_create_collection(collection_name)
            # Get all documents with metadata (no embedding needed)
            all_docs = collection.get(include=['documents', 'metadatas'])

            if not all_docs['ids']:
                return result

            # Group by file_name metadata
            grouped = {}
            for i, doc_id in enumerate(all_docs['ids']):
                metadata = all_docs['metadatas'][i] if all_docs['metadatas'] else {}
                file_name = metadata.get('file_name', 'Unknown')
                text = all_docs['documents'][i] if all_docs['documents'] else ''

                if file_name not in grouped:
                    grouped[file_name] = {
                        'file_name': file_name,
                        'chunk_count': 0,
                        'chunks': [],
                    }

                grouped[file_name]['chunk_count'] += 1
                grouped[file_name]['chunks'].append({
                    'id': doc_id,
                    'text': text,
                    'metadata': metadata,
                })

            result['documents'] = list(grouped.values())

        except Exception as e:
            result['error'] = str(e)

        return result


def main():
    """CLI interface for document processor."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AVACHATTER Document Processor")
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--db-path', default='./chroma_db',
                        help='Path to ChromaDB persistence directory (absolute recommended)')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process and index a document')
    process_parser.add_argument('file', help='Path to document')
    process_parser.add_argument('--collection', default='documents', help='Collection name')
    process_parser.add_argument('--no-ocr', action='store_true', help='Disable OCR')
    process_parser.add_argument('--password', help='PDF password')
    process_parser.add_argument('--chunk-size', type=int, default=500, help='Chunk size')
    process_parser.add_argument('--smart', action='store_true',
                                help='Use structure-aware chunking (preserves sections/headings)')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query indexed documents')
    query_parser.add_argument('query', help='Search query')
    query_parser.add_argument('--collection', default='documents', help='Collection name')
    query_parser.add_argument('--top-k', type=int, default=5, help='Number of results')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show collection statistics')
    stats_parser.add_argument('--collection', default='documents', help='Collection name')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple documents in one batch')
    batch_parser.add_argument('--files', nargs='+', required=True, help='Paths to documents')
    batch_parser.add_argument('--collection', default='documents', help='Collection name')
    batch_parser.add_argument('--no-ocr', action='store_true', help='Disable OCR')
    batch_parser.add_argument('--chunk-size', type=int, default=500, help='Chunk size')
    batch_parser.add_argument('--smart', action='store_true',
                              help='Use structure-aware chunking (preserves sections/headings)')

    # Health command
    health_parser = subparsers.add_parser('health', help='Check ChromaDB health')
    health_parser.add_argument('--collection', default='documents', help='Collection name')
    health_parser.add_argument('--auto-recover', action='store_true', help='Auto-recover corrupt DB')

    # List-by-source command
    list_source_parser = subparsers.add_parser('list-by-source', help='List documents grouped by source file')
    list_source_parser.add_argument('--collection', default='documents', help='Collection name')

    args = parser.parse_args()

    # Suppress progress output when in JSON mode
    if args.json:
        # Disable tqdm progress bars to avoid pipe buffer deadlocks
        os.environ['TQDM_DISABLE'] = '1'
        # Redirect stdout temporarily to capture only final JSON
        import io
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()

    # Initialize processor with the specified ChromaDB path
    processor = DocumentProcessor(vector_db_path=args.db_path)

    if args.command == 'process':
        result = processor.process_and_index_document(
            file_path=args.file,
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            use_ocr=not args.no_ocr,
            password=args.password,
            smart=args.smart
        )

        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(result))
        else:
            print("\n" + "=" * 80)
            if result['success']:
                print(f"[OK] Success: Created {result['chunks_created']} chunks")
            else:
                print(f"[ERROR] Error: {result['error']}")

    elif args.command == 'batch':
        result = processor.process_batch(
            file_paths=args.files,
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            use_ocr=not args.no_ocr,
            smart=args.smart,
        )

        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(result))
        else:
            print("\n" + "=" * 80)
            print(f"Batch complete: {result['success_count']}/{result['total_files']} succeeded, "
                  f"{result['error_count']} errors, {result['total_time']}s total")
            for r in result['results']:
                status = "OK" if r['success'] else "FAIL"
                print(f"  [{status}] {os.path.basename(r['file_path'])} — "
                      f"{r['chunks_created']} chunks, {r.get('processing_time', '?')}s"
                      f"{' — ' + r['error'] if r.get('error') else ''}")

    elif args.command == 'query':
        result = processor.query_documents(
            query=args.query,
            collection_name=args.collection,
            top_k=args.top_k
        )

        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(result))
        else:
            print("\n" + "=" * 80)
            if result['error']:
                print(f"[ERROR] Error: {result['error']}")
            else:
                print(f"Query: {result['query']}")
                print(f"Found {len(result['results'])} results:\n")
                for i, res in enumerate(result['results'], 1):
                    print(f"{i}. {res['metadata'].get('file_name', 'Unknown')}")
                    print(f"   Distance: {res['distance']:.4f}")
                    print(f"   Text: {res['text'][:100]}...")
                    print()

    elif args.command == 'stats':
        stats = processor.get_collection_stats(args.collection)

        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(stats))
        else:
            print("\n" + "=" * 80)
            print(f"Collection: {stats['collection']}")
            print(f"Documents: {stats['document_count']}")
            print(f"\nAll collections: {', '.join(stats['all_collections'])}")

    elif args.command == 'health':
        health = processor.check_health(
            collection_name=args.collection,
            auto_recover=args.auto_recover
        )

        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(health))
        else:
            print("\n" + "=" * 80)
            status = "Healthy" if health['healthy'] else "Unhealthy"
            print(f"ChromaDB Status: {status}")
            print(f"Documents: {health['document_count']}")
            if health['error']:
                print(f"Error: {health['error']}")
            if health['recovered']:
                print("Database was recovered automatically.")

    elif args.command == 'list-by-source':
        result = processor.list_by_source(args.collection)

        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(result))
        else:
            print("\n" + "=" * 80)
            if result['error']:
                print(f"[ERROR] {result['error']}")
            else:
                print(f"Found {len(result['documents'])} source documents:\n")
                for doc in result['documents']:
                    print(f"  {doc['file_name']} ({doc['chunk_count']} chunks)")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()

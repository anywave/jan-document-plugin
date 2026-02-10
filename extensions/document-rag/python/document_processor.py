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
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'docx',  # Try with docx processor
            '.txt': 'text',
            '.md': 'text',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.bmp': 'image',
            '.tiff': 'image',
            '.tif': 'image'
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
        password: Optional[str] = None
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
            print(f"Processing: {os.path.basename(file_path)}")

            # Step 1: Extract text
            print("  [1/4] Extracting text...")
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

            # Step 2: Chunk and embed
            print("  [2/4] Chunking text...")
            doc_result = self.embedder.embed_document(
                extract_result['text'],
                chunk_size=chunk_size,
                overlap=overlap,
                metadata=extract_result['metadata']
            )

            if doc_result['error']:
                result['error'] = f"Embedding failed: {doc_result['error']}"
                return result

            result['chunks_created'] = len(doc_result['chunks'])

            # Step 3: Prepare for storage
            print(f"  [3/4] Generated {len(doc_result['embeddings'])} embeddings")

            # Create unique IDs
            file_id = Path(file_path).stem
            doc_ids = [f"{file_id}_chunk_{i}" for i in range(len(doc_result['chunks']))]

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
            print("  [4/4] Storing in vector database...")
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

            result['success'] = True
            print("  ✓ Complete")

        except Exception as e:
            result['error'] = str(e)

        return result

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


def main():
    """CLI interface for document processor."""
    import argparse

    parser = argparse.ArgumentParser(description="AVACHATTER Document Processor")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process and index a document')
    process_parser.add_argument('file', help='Path to document')
    process_parser.add_argument('--collection', default='documents', help='Collection name')
    process_parser.add_argument('--no-ocr', action='store_true', help='Disable OCR')
    process_parser.add_argument('--password', help='PDF password')
    process_parser.add_argument('--chunk-size', type=int, default=500, help='Chunk size')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query indexed documents')
    query_parser.add_argument('query', help='Search query')
    query_parser.add_argument('--collection', default='documents', help='Collection name')
    query_parser.add_argument('--top-k', type=int, default=5, help='Number of results')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show collection statistics')
    stats_parser.add_argument('--collection', default='documents', help='Collection name')

    args = parser.parse_args()

    # Initialize processor
    processor = DocumentProcessor()

    if args.command == 'process':
        result = processor.process_and_index_document(
            file_path=args.file,
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            use_ocr=not args.no_ocr,
            password=args.password
        )

        print("\n" + "=" * 80)
        if result['success']:
            print(f"✓ Success: Created {result['chunks_created']} chunks")
        else:
            print(f"✗ Error: {result['error']}")

    elif args.command == 'query':
        result = processor.query_documents(
            query=args.query,
            collection_name=args.collection,
            top_k=args.top_k
        )

        print("\n" + "=" * 80)
        if result['error']:
            print(f"✗ Error: {result['error']}")
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
        print("\n" + "=" * 80)
        print(f"Collection: {stats['collection']}")
        print(f"Documents: {stats['document_count']}")
        print(f"\nAll collections: {', '.join(stats['all_collections'])}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()

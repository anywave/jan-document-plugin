#!/usr/bin/env python3
"""
Vector Store for AVACHATTER
Handles document vector storage and retrieval using ChromaDB.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os
from pathlib import Path


class VectorStore:
    """Manage vector storage for document embeddings."""

    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory,
            anonymized_telemetry=False  # IMPORTANT: Disable telemetry
        ))

        self.default_collection_name = "documents"

    def get_or_create_collection(
        self,
        collection_name: str = None,
        metadata: Optional[Dict] = None
    ):
        """
        Get existing collection or create new one.

        Args:
            collection_name: Name of collection
            metadata: Optional metadata for collection

        Returns:
            Collection object
        """
        if collection_name is None:
            collection_name = self.default_collection_name

        return self.client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or {}
        )

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: List[str],
        collection_name: str = None
    ) -> Dict[str, any]:
        """
        Add documents to vector store.

        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: List of unique document IDs
            collection_name: Collection to add to

        Returns:
            Dictionary with result status
        """
        result = {
            'success': False,
            'added': 0,
            'error': None
        }

        try:
            collection = self.get_or_create_collection(collection_name)

            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            result['success'] = True
            result['added'] = len(documents)

        except Exception as e:
            result['error'] = str(e)

        return result

    def query_documents(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        collection_name: str = None,
        where_filter: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Query vector store for similar documents.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            collection_name: Collection to query
            where_filter: Optional metadata filter

        Returns:
            Dictionary with:
                - ids: List of document IDs
                - documents: List of document texts
                - metadatas: List of metadata dicts
                - distances: List of similarity distances
        """
        result = {
            'ids': [],
            'documents': [],
            'metadatas': [],
            'distances': [],
            'error': None
        }

        try:
            collection = self.get_or_create_collection(collection_name)

            query_result = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )

            if query_result['ids']:
                result['ids'] = query_result['ids'][0]
                result['documents'] = query_result['documents'][0]
                result['metadatas'] = query_result['metadatas'][0]
                result['distances'] = query_result['distances'][0]

        except Exception as e:
            result['error'] = str(e)

        return result

    def get_document(
        self,
        doc_id: str,
        collection_name: str = None
    ) -> Optional[Dict]:
        """
        Retrieve a specific document by ID.

        Args:
            doc_id: Document ID
            collection_name: Collection to search

        Returns:
            Dictionary with document data or None
        """
        try:
            collection = self.get_or_create_collection(collection_name)

            result = collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas', 'embeddings']
            )

            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0],
                    'metadata': result['metadatas'][0],
                    'embedding': result['embeddings'][0]
                }

        except Exception:
            pass

        return None

    def delete_documents(
        self,
        doc_ids: List[str],
        collection_name: str = None
    ) -> Dict[str, any]:
        """
        Delete documents from vector store.

        Args:
            doc_ids: List of document IDs to delete
            collection_name: Collection to delete from

        Returns:
            Dictionary with result status
        """
        result = {
            'success': False,
            'deleted': 0,
            'error': None
        }

        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=doc_ids)

            result['success'] = True
            result['deleted'] = len(doc_ids)

        except Exception as e:
            result['error'] = str(e)

        return result

    def list_collections(self) -> List[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except:
            return []

    def get_collection_count(self, collection_name: str = None) -> int:
        """
        Get number of documents in collection.

        Args:
            collection_name: Collection to count

        Returns:
            Number of documents
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except:
            return 0

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete entire collection.

        Args:
            collection_name: Collection to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(name=collection_name)
            return True
        except:
            return False

    def persist(self):
        """Persist all changes to disk."""
        try:
            self.client.persist()
        except:
            pass


def main():
    """Test the vector store."""
    import numpy as np

    print("Initializing vector store...")
    store = VectorStore("./test_chroma_db")

    # Create test data
    print("\nCreating test documents...")
    test_docs = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is a subset of artificial intelligence",
        "Python is a popular programming language"
    ]

    # Generate dummy embeddings (in real use, these come from embedder.py)
    test_embeddings = [
        np.random.rand(384).tolist() for _ in test_docs
    ]

    test_metadatas = [
        {'source': 'test1.txt', 'type': 'text'},
        {'source': 'test2.txt', 'type': 'text'},
        {'source': 'test3.txt', 'type': 'text'}
    ]

    test_ids = ['doc1', 'doc2', 'doc3']

    # Add documents
    print("Adding documents to vector store...")
    result = store.add_documents(
        documents=test_docs,
        embeddings=test_embeddings,
        metadatas=test_metadatas,
        ids=test_ids
    )

    if result['success']:
        print(f"✓ Added {result['added']} documents")
    else:
        print(f"✗ Error: {result['error']}")
        return

    # Count documents
    count = store.get_collection_count()
    print(f"✓ Collection contains {count} documents")

    # Query with dummy embedding
    print("\nQuerying vector store...")
    query_embedding = np.random.rand(384).tolist()
    query_result = store.query_documents(query_embedding, n_results=2)

    if not query_result['error']:
        print(f"✓ Found {len(query_result['ids'])} results")
        for i, doc_id in enumerate(query_result['ids']):
            print(f"  {i+1}. ID: {doc_id}")
            print(f"     Text: {query_result['documents'][i][:50]}...")
            print(f"     Distance: {query_result['distances'][i]:.4f}")
    else:
        print(f"✗ Query error: {query_result['error']}")

    # Get specific document
    print("\nRetrieving specific document...")
    doc = store.get_document('doc2')
    if doc:
        print(f"✓ Retrieved document: {doc['document'][:50]}...")
    else:
        print("✗ Document not found")

    # List collections
    print("\nCollections:")
    collections = store.list_collections()
    for col in collections:
        print(f"  - {col}")

    # Clean up
    print("\nCleaning up test data...")
    store.delete_collection("documents")
    print("✓ Test complete")


if __name__ == '__main__':
    main()

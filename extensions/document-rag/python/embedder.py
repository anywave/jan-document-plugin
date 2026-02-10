#!/usr/bin/env python3
"""
Embedder for AVACHATTER
Generates text embeddings using all-MiniLM-L6-v2 model.
"""

from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np


class Embedder:
    """Generate embeddings for text documents."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', device: str = 'cpu'):
        """
        Initialize embedder.

        Args:
            model_name: HuggingFace model name
            device: Device to run model on ('cpu' or 'cuda')
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension

    def load_model(self):
        """Load the embedding model."""
        if self.model is None:
            print(f"Loading model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            print("✓ Model loaded")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector (384 dimensions)
        """
        self.load_model()

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors
        """
        self.load_model()

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings.tolist()

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[Dict[str, any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text
            chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters

        Returns:
            List of dictionaries with 'text', 'start', 'end'
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end markers
                for marker in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    last_marker = text[start:end].rfind(marker)
                    if last_marker != -1:
                        end = start + last_marker + 1
                        break

            chunk = {
                'text': text[start:end].strip(),
                'start': start,
                'end': end
            }

            if chunk['text']:
                chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - overlap if end < len(text) else end

        return chunks

    def embed_document(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
        metadata: Dict = None
    ) -> Dict[str, any]:
        """
        Process document: chunk text and generate embeddings.

        Args:
            text: Document text
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            metadata: Optional metadata to attach

        Returns:
            Dictionary with:
                - chunks: List of text chunks
                - embeddings: List of embedding vectors
                - metadata: Document metadata
        """
        result = {
            'chunks': [],
            'embeddings': [],
            'metadata': metadata or {},
            'error': None
        }

        try:
            # Chunk text
            chunks = self.chunk_text(text, chunk_size, overlap)
            result['chunks'] = chunks

            # Generate embeddings
            chunk_texts = [c['text'] for c in chunks]
            embeddings = self.embed_texts(chunk_texts, show_progress=True)
            result['embeddings'] = embeddings

        except Exception as e:
            result['error'] = str(e)

        return result

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1, higher = more similar)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar embeddings to query.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embeddings
            top_k: Number of results to return

        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        similarities = []

        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(query_embedding, candidate)
            similarities.append((i, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]


def main():
    """Test the embedder."""
    print("Initializing embedder...")
    embedder = Embedder()

    # Test single text embedding
    print("\nTest 1: Single text embedding")
    text = "The quick brown fox jumps over the lazy dog"
    print(f"Text: {text}")
    embedding = embedder.embed_text(text)
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")

    # Test multiple texts
    print("\nTest 2: Multiple text embeddings")
    texts = [
        "Machine learning is a subset of artificial intelligence",
        "Python is a popular programming language",
        "The weather is nice today"
    ]
    embeddings = embedder.embed_texts(texts)
    print(f"Generated {len(embeddings)} embeddings")

    # Test text chunking
    print("\nTest 3: Text chunking")
    long_text = """
    This is a test document. It contains multiple sentences.
    The embedder will chunk this text into smaller pieces.
    Each chunk will have some overlap with adjacent chunks.
    This helps maintain context across chunk boundaries.
    """
    chunks = embedder.chunk_text(long_text, chunk_size=100, overlap=20)
    print(f"Split text into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}: {chunk['text'][:50]}...")

    # Test document embedding
    print("\nTest 4: Document embedding with chunking")
    result = embedder.embed_document(
        long_text,
        chunk_size=100,
        overlap=20,
        metadata={'source': 'test.txt'}
    )
    if not result['error']:
        print(f"✓ Document chunked into {len(result['chunks'])} pieces")
        print(f"✓ Generated {len(result['embeddings'])} embeddings")
    else:
        print(f"✗ Error: {result['error']}")

    # Test similarity
    print("\nTest 5: Similarity computation")
    sim = embedder.compute_similarity(embeddings[0], embeddings[1])
    print(f"Similarity between text 1 and text 2: {sim:.4f}")
    sim = embedder.compute_similarity(embeddings[0], embeddings[0])
    print(f"Similarity between text 1 and itself: {sim:.4f}")

    # Test finding most similar
    print("\nTest 6: Finding most similar")
    query_embedding = embedder.embed_text("Artificial intelligence and ML")
    most_similar = embedder.find_most_similar(query_embedding, embeddings, top_k=2)
    print("Most similar texts:")
    for idx, score in most_similar:
        print(f"  - '{texts[idx]}' (similarity: {score:.4f})")

    print("\n✓ All tests complete")


if __name__ == '__main__':
    main()

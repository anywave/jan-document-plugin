# MOBIUS Document RAG Extension - Python Backend

**Version**: 1.0.0
**Python**: 3.12+
**Offline**: 100%

## Overview

This Python backend handles document processing, OCR, text embedding, and vector storage for MOBIUS's document RAG system.

## Components

### 1. `pdf_processor.py`
Extracts text from PDF files with OCR support for scanned documents.

**Features**:
- Direct text extraction from PDFs
- OCR fallback for scanned pages (Tesseract)
- PDF decryption (pikepdf)
- Metadata extraction
- Auto-detection of scanned PDFs

**Usage**:
```python
from pdf_processor import PDFProcessor

processor = PDFProcessor(tesseract_path="C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
result = processor.extract_text("document.pdf", use_ocr=True)
print(result['text'])
```

### 2. `docx_processor.py`
Extracts text from Microsoft Word documents.

**Features**:
- Paragraph extraction
- Table text extraction
- Metadata extraction
- Heading structure analysis

**Usage**:
```python
from docx_processor import DOCXProcessor

processor = DOCXProcessor()
result = processor.extract_text("document.docx")
print(result['text'])
```

### 3. `image_processor.py`
Performs OCR on images to extract text.

**Features**:
- Image preprocessing for better OCR
- Multiple format support (PNG, JPG, TIFF, etc.)
- Text region detection
- Confidence scoring

**Usage**:
```python
from image_processor import ImageProcessor

processor = ImageProcessor(tesseract_path="C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
result = processor.extract_text("scan.png", preprocess=True)
print(result['text'])
```

### 4. `embedder.py`
Generates text embeddings using all-MiniLM-L6-v2 model.

**Features**:
- 384-dimensional embeddings
- Text chunking with overlap
- Batch processing
- Similarity computation

**Usage**:
```python
from embedder import Embedder

embedder = Embedder()
embedding = embedder.embed_text("Sample text")
print(f"Embedding dimension: {len(embedding)}")
```

### 5. `vector_store.py`
Manages document storage and retrieval using ChromaDB.

**Features**:
- Vector similarity search
- Persistent storage
- Collection management
- CRUD operations

**Usage**:
```python
from vector_store import VectorStore

store = VectorStore("./chroma_db")
store.add_documents(
    documents=["text"],
    embeddings=[embedding],
    metadatas=[{"source": "file.txt"}],
    ids=["doc1"]
)
```

### 6. `document_processor.py`
Main orchestrator for the complete processing pipeline.

**Features**:
- Auto file type detection
- Complete extract → chunk → embed → store pipeline
- Query interface
- CLI tool

**Usage**:
```python
from document_processor import DocumentProcessor

processor = DocumentProcessor()

# Process and index
result = processor.process_and_index_document("document.pdf")

# Query
results = processor.query_documents("search query", top_k=5)
```

## Installation

### Requirements
- Python 3.12+
- Tesseract OCR (Windows: install separately)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install Tesseract OCR
**Windows**:
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR\`
3. Add to PATH or specify path in code

## CLI Usage

### Process a Document
```bash
python document_processor.py process document.pdf
python document_processor.py process --no-ocr document.pdf
python document_processor.py process --password mypass encrypted.pdf
```

### Query Documents
```bash
python document_processor.py query "machine learning"
python document_processor.py query "AI algorithms" --top-k 10
```

### View Statistics
```bash
python document_processor.py stats
python document_processor.py stats --collection my_docs
```

## Testing

Each processor includes a standalone test in its `if __name__ == '__main__'` block.

```bash
# Test PDF processor
python pdf_processor.py sample.pdf

# Test DOCX processor
python docx_processor.py sample.docx

# Test image processor
python image_processor.py scan.png

# Test embedder
python embedder.py

# Test vector store
python vector_store.py
```

## Dependencies

### Core Libraries
- **PyMuPDF** (fitz): PDF text extraction
- **pikepdf**: PDF encryption handling
- **python-docx**: Word document processing
- **Pillow**: Image manipulation
- **pytesseract**: Tesseract OCR wrapper

### ML/Vector Libraries
- **sentence-transformers**: Embedding model
- **chromadb**: Vector database
- **torch**: PyTorch (CPU only)
- **transformers**: HuggingFace transformers

### Utilities
- **numpy**: Numerical operations
- **tqdm**: Progress bars

## Model Details

### all-MiniLM-L6-v2
- **Type**: Sentence transformer
- **Dimensions**: 384
- **Size**: ~90MB
- **Speed**: Fast (CPU-friendly)
- **Quality**: Good for general-purpose semantic search

**First run**: Model will be downloaded from HuggingFace
**After**: Model cached locally in `~/.cache/huggingface/`

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   document_processor.py                  │
│                 (Main Orchestrator)                      │
└───────────────────────────┬─────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │pdf_processor │ │docx_processor│ │image_processor│
    └──────────────┘ └──────────────┘ └──────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   embedder   │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ vector_store │
                    └──────────────┘
```

## Performance

### Processing Speed (Estimated)
- **Text PDF** (10 pages): ~2 seconds
- **Scanned PDF** (10 pages): ~30 seconds (OCR)
- **DOCX** (10 pages): ~1 second
- **Image OCR**: ~2-5 seconds per image

### Embedding Speed
- **CPU**: ~50 documents/second
- **Batch of 100**: ~2 seconds total

### Storage
- **ChromaDB**: Persistent, ~1KB per document chunk
- **Model Cache**: ~90MB (one-time download)

## Error Handling

All processors return dictionaries with an `error` field:

```python
result = processor.extract_text("file.pdf")
if result['error']:
    print(f"Failed: {result['error']}")
else:
    print(f"Success: {len(result['text'])} characters")
```

## Troubleshooting

### "Tesseract not found"
- Install Tesseract OCR
- Set path: `processor = PDFProcessor(tesseract_path="C:\\Path\\To\\tesseract.exe")`

### "Model download failed"
- Check internet connection (one-time download)
- Model saved to: `~/.cache/huggingface/hub/`

### "ChromaDB error"
- Check write permissions on `./chroma_db/` directory
- Ensure disk space available

### "Out of memory"
- Reduce batch size in embedder
- Process large PDFs in smaller chunks
- Use CPU-only torch build (default)

## Integration with MOBIUS

These Python scripts will be called via Tauri IPC from the Electron/React frontend:

```typescript
// Example Tauri command (Phase 3)
const result = await invoke('process_document', {
  filePath: '/path/to/document.pdf',
  useOcr: true
});
```

## License

Part of MOBIUS project - 100% offline document AI assistant.

## Credits

Built on:
- PyMuPDF (PDF processing)
- Tesseract OCR (Google)
- sentence-transformers (UKPLab)
- ChromaDB (Chroma)

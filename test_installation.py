#!/usr/bin/env python
"""
Quick test script to verify Jan Document Plugin installation.

Usage:
    python test_installation.py
"""

import sys
from pathlib import Path

def test_imports():
    """Test all required imports."""
    print("Testing imports...")
    
    errors = []
    
    # Core dependencies
    deps = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("httpx", "HTTP client"),
        ("fitz", "PyMuPDF for PDF extraction"),
        ("docx", "python-docx for Word documents"),
        ("openpyxl", "Excel file support"),
        ("PIL", "Pillow for image handling"),
        ("pytesseract", "Tesseract OCR wrapper"),
        ("sentence_transformers", "Local embeddings"),
        ("chromadb", "Vector database"),
        ("pydantic", "Data validation"),
    ]
    
    for module, desc in deps:
        try:
            __import__(module)
            print(f"  ✓ {module}: {desc}")
        except ImportError as e:
            print(f"  ✗ {module}: {desc} - MISSING")
            errors.append((module, str(e)))
    
    return errors


def test_tesseract():
    """Test Tesseract OCR availability."""
    print("\nTesting Tesseract OCR...")
    
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"  ✓ Tesseract version: {version}")
        return True
    except Exception as e:
        print(f"  ⚠ Tesseract not available: {e}")
        print("    OCR features will be disabled.")
        print("    Install from: https://github.com/tesseract-ocr/tesseract")
        return False


def test_embedding_model():
    """Test sentence-transformers model loading."""
    print("\nTesting embedding model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        print("  Loading model (may download on first run)...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Quick test
        embedding = model.encode(["test sentence"])
        print(f"  ✓ Model loaded. Embedding dimension: {embedding.shape[1]}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load model: {e}")
        return False


def test_document_processor():
    """Test document processor initialization."""
    print("\nTesting document processor...")
    
    try:
        from document_processor import DocumentProcessor
        
        processor = DocumentProcessor(persist_directory=None)  # Ephemeral
        stats = processor.get_stats()
        
        print(f"  ✓ Processor initialized")
        print(f"    Supported extensions: {len(stats['supported_extensions'])}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to initialize: {e}")
        return False


def test_sample_extraction():
    """Test basic text extraction (if test file exists)."""
    print("\nTesting text extraction...")
    
    # Create a simple test file
    test_file = Path("test_document.txt")
    test_content = "This is a test document for the Jan Document Plugin."
    
    try:
        test_file.write_text(test_content)
        
        from document_processor import DocumentExtractor
        
        extractor = DocumentExtractor()
        extracted = extractor.extract(test_file)
        
        if test_content in extracted:
            print(f"  ✓ Text extraction working")
            return True
        else:
            print(f"  ✗ Extraction mismatch")
            return False
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        return False
    finally:
        if test_file.exists():
            test_file.unlink()


def main():
    print("=" * 60)
    print("Jan Document Plugin - Installation Test")
    print("=" * 60)
    
    # Run tests
    import_errors = test_imports()
    tesseract_ok = test_tesseract()
    embedding_ok = test_embedding_model()
    processor_ok = test_document_processor()
    extraction_ok = test_sample_extraction()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if import_errors:
        print(f"\n⚠ Missing dependencies ({len(import_errors)}):")
        for module, error in import_errors:
            print(f"  - {module}")
        print("\nRun: pip install -r requirements.txt")
        sys.exit(1)
    
    if not embedding_ok or not processor_ok:
        print("\n✗ Core functionality not working")
        sys.exit(1)
    
    print("\n✓ All core tests passed!")
    
    if not tesseract_ok:
        print("  (OCR disabled - install Tesseract for image/scanned PDF support)")
    
    print("\nReady to run:")
    print("  python jan_proxy.py --port 1338")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

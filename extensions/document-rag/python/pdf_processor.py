#!/usr/bin/env python3
"""
PDF Processor for AVACHATTER
Handles PDF text extraction with OCR fallback and decryption support.
"""

import fitz  # PyMuPDF
import pytesseract
import pikepdf
from PIL import Image
import io
import os
from typing import Dict, List, Optional
from pathlib import Path


class PDFProcessor:
    """Extract text from PDF files with OCR support for scanned documents."""

    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize PDF processor.

        Args:
            tesseract_path: Path to Tesseract executable (Windows: tesseract.exe)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_text(
        self,
        pdf_path: str,
        use_ocr: bool = True,
        password: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file
            use_ocr: Whether to use OCR for scanned pages
            password: Password for encrypted PDFs

        Returns:
            Dictionary with:
                - text: Extracted text
                - pages: Number of pages
                - is_scanned: Whether OCR was used
                - metadata: PDF metadata
        """
        result = {
            'text': '',
            'pages': 0,
            'is_scanned': False,
            'metadata': {},
            'error': None
        }

        try:
            # Try to decrypt if password provided
            if password:
                pdf_path = self._decrypt_pdf(pdf_path, password)

            # Open PDF
            doc = fitz.open(pdf_path)
            result['pages'] = doc.page_count
            result['metadata'] = doc.metadata

            text_chunks = []
            used_ocr = False

            # Extract text from each page
            for page_num in range(doc.page_count):
                page = doc[page_num]

                # Try direct text extraction first
                page_text = page.get_text()

                # If little/no text found and OCR enabled, use OCR
                if len(page_text.strip()) < 50 and use_ocr:
                    page_text = self._ocr_page(page)
                    used_ocr = True

                text_chunks.append(page_text)

            result['text'] = '\n\n'.join(text_chunks)
            result['is_scanned'] = used_ocr
            doc.close()

        except Exception as e:
            result['error'] = str(e)

        return result

    def _decrypt_pdf(self, pdf_path: str, password: str) -> str:
        """
        Decrypt an encrypted PDF.

        Args:
            pdf_path: Path to encrypted PDF
            password: PDF password

        Returns:
            Path to decrypted PDF (temporary file)
        """
        try:
            with pikepdf.open(pdf_path, password=password) as pdf:
                # Create temporary decrypted file
                temp_path = pdf_path.replace('.pdf', '_decrypted.pdf')
                pdf.save(temp_path)
                return temp_path
        except pikepdf.PasswordError:
            raise ValueError("Invalid PDF password")

    def _ocr_page(self, page: fitz.Page, dpi: int = 300) -> str:
        """
        Perform OCR on a PDF page.

        Args:
            page: PyMuPDF page object
            dpi: Resolution for rendering (higher = better quality, slower)

        Returns:
            Extracted text from OCR
        """
        try:
            # Render page to image
            pix = page.get_pixmap(dpi=dpi)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            # Perform OCR
            text = pytesseract.image_to_string(image)

            return text
        except Exception as e:
            return f"[OCR Error: {str(e)}]"

    def extract_metadata(self, pdf_path: str) -> Dict[str, str]:
        """
        Extract PDF metadata only.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary of metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            doc.close()
            return metadata
        except Exception as e:
            return {'error': str(e)}

    def is_encrypted(self, pdf_path: str) -> bool:
        """
        Check if PDF is encrypted.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if encrypted, False otherwise
        """
        try:
            doc = fitz.open(pdf_path)
            encrypted = doc.is_encrypted
            doc.close()
            return encrypted
        except:
            return False

    def check_needs_ocr(self, pdf_path: str, threshold: int = 100) -> bool:
        """
        Determine if PDF is likely scanned and needs OCR.

        Args:
            pdf_path: Path to PDF file
            threshold: Minimum text length to consider as non-scanned

        Returns:
            True if PDF appears to be scanned
        """
        try:
            doc = fitz.open(pdf_path)

            # Check first 3 pages
            pages_to_check = min(3, doc.page_count)
            total_text_length = 0

            for page_num in range(pages_to_check):
                page = doc[page_num]
                text = page.get_text()
                total_text_length += len(text.strip())

            doc.close()

            # If average text per page is below threshold, likely scanned
            avg_text_per_page = total_text_length / pages_to_check
            return avg_text_per_page < threshold

        except Exception:
            return True  # Assume needs OCR on error


def main():
    """Test the PDF processor."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_processor.py <pdf_file> [password]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else None

    processor = PDFProcessor()

    # Check if encrypted
    if processor.is_encrypted(pdf_path):
        print("PDF is encrypted")
        if not password:
            print("Password required but not provided")
            sys.exit(1)

    # Check if needs OCR
    needs_ocr = processor.check_needs_ocr(pdf_path)
    print(f"PDF appears to {'need' if needs_ocr else 'not need'} OCR")

    # Extract text
    print("Extracting text...")
    result = processor.extract_text(pdf_path, use_ocr=True, password=password)

    if result['error']:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"\nPages: {result['pages']}")
    print(f"Used OCR: {result['is_scanned']}")
    print(f"\nMetadata: {result['metadata']}")
    print(f"\nExtracted Text ({len(result['text'])} characters):")
    print("=" * 80)
    print(result['text'][:1000])  # Print first 1000 chars
    if len(result['text']) > 1000:
        print("...")


if __name__ == '__main__':
    main()

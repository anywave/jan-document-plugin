#!/usr/bin/env python3
"""
Image Processor for AVACHATTER
Handles OCR text extraction from images.
"""

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from typing import Dict, Optional
import os


class ImageProcessor:
    """Extract text from images using OCR."""

    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize image processor.

        Args:
            tesseract_path: Path to Tesseract executable
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_text(
        self,
        image_path: str,
        preprocess: bool = True,
        language: str = 'eng'
    ) -> Dict[str, any]:
        """
        Extract text from image using OCR.

        Args:
            image_path: Path to image file
            preprocess: Whether to preprocess image for better OCR
            language: Tesseract language code (eng, fra, deu, etc.)

        Returns:
            Dictionary with:
                - text: Extracted text
                - confidence: OCR confidence (0-100)
                - size: Image dimensions
                - format: Image format
        """
        result = {
            'text': '',
            'confidence': 0,
            'size': (0, 0),
            'format': '',
            'error': None
        }

        try:
            # Open image
            image = Image.open(image_path)
            result['size'] = image.size
            result['format'] = image.format

            # Preprocess if enabled
            if preprocess:
                image = self._preprocess_image(image)

            # Perform OCR
            result['text'] = pytesseract.image_to_string(image, lang=language)

            # Get confidence data
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            if confidences:
                result['confidence'] = sum(confidences) / len(confidences)

        except Exception as e:
            result['error'] = str(e)

        return result

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.

        Args:
            image: PIL Image object

        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)

        # Apply slight denoising
        image = image.filter(ImageFilter.MedianFilter(size=3))

        return image

    def extract_text_regions(
        self,
        image_path: str,
        language: str = 'eng'
    ) -> list[Dict[str, any]]:
        """
        Extract text with bounding boxes.

        Args:
            image_path: Path to image file
            language: Tesseract language code

        Returns:
            List of dictionaries with text and position data
        """
        regions = []

        try:
            image = Image.open(image_path)

            # Get OCR data with bounding boxes
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)

            n_boxes = len(data['level'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:  # Only confident detections
                    region = {
                        'text': data['text'][i],
                        'confidence': int(data['conf'][i]),
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    }
                    regions.append(region)

        except Exception as e:
            regions.append({'error': str(e)})

        return regions

    def detect_text_presence(self, image_path: str, threshold: int = 50) -> bool:
        """
        Detect if image contains significant text.

        Args:
            image_path: Path to image file
            threshold: Minimum text length to consider as containing text

        Returns:
            True if text detected
        """
        try:
            result = self.extract_text(image_path, preprocess=False)
            return len(result['text'].strip()) > threshold and result['error'] is None
        except:
            return False

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported image formats.

        Returns:
            List of file extensions
        """
        return ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp']


def main():
    """Test the image processor."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_processor.py <image_file> [language]")
        print("Supported languages: eng (English), fra (French), deu (German), etc.")
        sys.exit(1)

    image_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'eng'

    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        sys.exit(1)

    processor = ImageProcessor()

    # Check if text is present
    has_text = processor.detect_text_presence(image_path)
    print(f"Text detected: {has_text}")

    if not has_text:
        print("No significant text found in image")
        sys.exit(0)

    # Extract text with preprocessing
    print("\nExtracting text with preprocessing...")
    result = processor.extract_text(image_path, preprocess=True, language=language)

    if result['error']:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"\nImage Size: {result['size']}")
    print(f"Format: {result['format']}")
    print(f"OCR Confidence: {result['confidence']:.1f}%")
    print(f"\nExtracted Text ({len(result['text'])} characters):")
    print("=" * 80)
    print(result['text'])

    # Extract regions
    print("\n\nText Regions (first 10):")
    print("=" * 80)
    regions = processor.extract_text_regions(image_path, language)
    for i, region in enumerate(regions[:10]):
        if 'error' not in region:
            print(f"Region {i+1}: '{region['text']}' "
                  f"(confidence: {region['confidence']}%, "
                  f"pos: {region['left']},{region['top']})")


if __name__ == '__main__':
    main()

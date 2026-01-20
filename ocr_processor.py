"""
OCR Pre-processing and Post-processing Pipeline

Handles two-step processing for scanned PDFs and images:
1. Pre-processing: Image enhancement before Tesseract OCR
2. Post-processing: Text cleanup after OCR to fix common artifacts

This ensures OCR artifacts are correctly handled for better RAG results.
"""

import re
import os
import logging
from typing import Optional, Tuple
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


def _configure_tesseract():
    """Auto-detect and configure Tesseract path for pytesseract."""
    import pytesseract

    # Check if already configured via environment
    env_path = os.environ.get("TESSERACT_CMD", "")
    if env_path and os.path.exists(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        return env_path

    # Common Windows installation paths
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in tesseract_paths:
        if path and os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract configured: {path}")
            return path

    return None


# Configure Tesseract on module import
_TESSERACT_PATH = _configure_tesseract()

# Try to import OpenCV - graceful fallback if not available
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available. OCR pre-processing will be limited.")


class OCRPreProcessor:
    """
    Image enhancement pipeline to improve OCR accuracy.

    Applies a sequence of image processing techniques:
    1. Grayscale conversion
    2. Contrast enhancement (CLAHE)
    3. Noise reduction (bilateral filter)
    4. Deskewing (rotation correction)
    5. Binarization (adaptive thresholding)
    """

    def __init__(
        self,
        apply_grayscale: bool = True,
        apply_contrast: bool = True,
        apply_denoise: bool = True,
        apply_deskew: bool = True,
        apply_threshold: bool = True,
        target_dpi: int = 300
    ):
        """
        Initialize pre-processor with configurable steps.

        Args:
            apply_grayscale: Convert to grayscale
            apply_contrast: Apply CLAHE contrast enhancement
            apply_denoise: Apply bilateral filter for noise reduction
            apply_deskew: Attempt rotation correction
            apply_threshold: Apply adaptive thresholding (binarization)
            target_dpi: Target DPI for resizing (higher = better OCR, slower)
        """
        self.apply_grayscale = apply_grayscale
        self.apply_contrast = apply_contrast
        self.apply_denoise = apply_denoise
        self.apply_deskew = apply_deskew
        self.apply_threshold = apply_threshold
        self.target_dpi = target_dpi

    def process(self, image: Image.Image) -> Image.Image:
        """
        Apply full pre-processing pipeline to image.

        Args:
            image: PIL Image to process

        Returns:
            Processed PIL Image ready for OCR
        """
        if not OPENCV_AVAILABLE:
            # Fallback: just convert to RGB
            logger.debug("OpenCV not available, using basic processing")
            return self._basic_process(image)

        # Convert PIL to OpenCV format (BGR)
        img_array = np.array(image)

        # Handle different color modes
        if len(img_array.shape) == 2:
            # Already grayscale
            gray = img_array
        elif img_array.shape[2] == 4:
            # RGBA -> BGR -> Gray
            bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if self.apply_grayscale else bgr
        else:
            # RGB -> BGR -> Gray
            bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if self.apply_grayscale else bgr

        processed = gray

        # Step 1: Contrast enhancement (CLAHE)
        if self.apply_contrast and len(processed.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            processed = clahe.apply(processed)
            logger.debug("Applied CLAHE contrast enhancement")

        # Step 2: Noise reduction
        if self.apply_denoise:
            if len(processed.shape) == 2:
                # For grayscale, use non-local means
                processed = cv2.fastNlMeansDenoising(processed, h=10)
            else:
                processed = cv2.bilateralFilter(processed, 9, 75, 75)
            logger.debug("Applied noise reduction")

        # Step 3: Deskew (rotation correction)
        if self.apply_deskew and len(processed.shape) == 2:
            processed = self._deskew(processed)
            logger.debug("Applied deskew correction")

        # Step 4: Adaptive thresholding (binarization)
        if self.apply_threshold and len(processed.shape) == 2:
            processed = cv2.adaptiveThreshold(
                processed, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            logger.debug("Applied adaptive thresholding")

        # Convert back to PIL Image
        if len(processed.shape) == 2:
            return Image.fromarray(processed, mode='L')
        else:
            return Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Correct skew in scanned documents.

        Uses Hough line detection to find dominant angle and rotate.
        """
        try:
            # Edge detection
            edges = cv2.Canny(image, 50, 150, apertureSize=3)

            # Hough line detection
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, 100,
                minLineLength=100, maxLineGap=10
            )

            if lines is None or len(lines) == 0:
                return image

            # Calculate average angle
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                # Only consider near-horizontal lines
                if abs(angle) < 45:
                    angles.append(angle)

            if not angles:
                return image

            median_angle = np.median(angles)

            # Only correct if skew is significant but not too extreme
            if abs(median_angle) < 0.5 or abs(median_angle) > 15:
                return image

            # Rotate image
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                image, rotation_matrix, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )

            logger.debug(f"Deskewed by {median_angle:.2f} degrees")
            return rotated

        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
            return image

    def _basic_process(self, image: Image.Image) -> Image.Image:
        """Basic processing when OpenCV is not available."""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Basic contrast enhancement using PIL
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        return image


class OCRPostProcessor:
    """
    Text cleanup pipeline to fix common OCR artifacts.

    Addresses issues like:
    - Broken words across lines
    - Common character confusions (rn -> m, cl -> d, etc.)
    - Extra whitespace and line breaks
    - Ligature issues (fi, fl, ff)
    - Number/letter confusions (0/O, 1/l/I)
    """

    # Common OCR character confusions
    CHAR_SUBSTITUTIONS = {
        'rn': 'm',   # Very common OCR error
        'vv': 'w',   # v+v looks like w
        'cl': 'd',   # c+l looks like d
        'cI': 'd',   # c+I looks like d
        '|': 'l',    # pipe vs lowercase L
        '0': 'O',    # Only in word context, not numbers
    }

    # Common OCR word errors
    WORD_CORRECTIONS = {
        'tbe': 'the',
        'tbat': 'that',
        'witb': 'with',
        'wbich': 'which',
        'frorn': 'from',
        'tbis': 'this',
        'rnore': 'more',
        'tirne': 'time',
        'sorne': 'some',
        'corne': 'come',
        'becorne': 'become',
        'narne': 'name',
        'sarne': 'same',
        'bave': 'have',
        'rnay': 'may',
        'rnake': 'make',
        'rnust': 'must',
    }

    def __init__(
        self,
        fix_broken_words: bool = True,
        fix_char_confusions: bool = True,
        fix_whitespace: bool = True,
        fix_common_words: bool = True,
        preserve_paragraphs: bool = True
    ):
        """
        Initialize post-processor with configurable corrections.

        Args:
            fix_broken_words: Merge words broken across lines
            fix_char_confusions: Fix common character substitution errors
            fix_whitespace: Normalize whitespace
            fix_common_words: Fix known common word errors
            preserve_paragraphs: Keep paragraph breaks (double newlines)
        """
        self.fix_broken_words = fix_broken_words
        self.fix_char_confusions = fix_char_confusions
        self.fix_whitespace = fix_whitespace
        self.fix_common_words = fix_common_words
        self.preserve_paragraphs = preserve_paragraphs

    def process(self, text: str) -> str:
        """
        Apply full post-processing pipeline to OCR text.

        Args:
            text: Raw OCR output text

        Returns:
            Cleaned text with artifacts removed
        """
        if not text:
            return text

        original_length = len(text)

        # Step 1: Fix broken words (hyphenated line breaks)
        if self.fix_broken_words:
            text = self._fix_broken_words(text)

        # Step 2: Normalize whitespace
        if self.fix_whitespace:
            text = self._normalize_whitespace(text)

        # Step 3: Fix character confusions
        if self.fix_char_confusions:
            text = self._fix_char_confusions(text)

        # Step 4: Fix common word errors
        if self.fix_common_words:
            text = self._fix_common_words(text)

        # Step 5: Final cleanup
        text = self._final_cleanup(text)

        if len(text) != original_length:
            logger.debug(f"OCR post-processing: {original_length} -> {len(text)} chars")

        return text

    def _fix_broken_words(self, text: str) -> str:
        """Fix words broken across lines with hyphens."""
        # Pattern: word- followed by newline and continuation
        # Example: "docu-\nment" -> "document"
        pattern = r'(\w+)-\s*\n\s*(\w+)'
        text = re.sub(pattern, r'\1\2', text)

        # Also handle soft hyphens
        text = text.replace('\u00ad', '')  # Soft hyphen
        text = text.replace('\u2010', '-')  # Hyphen
        text = text.replace('\u2011', '-')  # Non-breaking hyphen

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph structure."""
        # Replace various Unicode spaces with regular space
        space_chars = [
            '\u00a0',  # Non-breaking space
            '\u2000',  # En quad
            '\u2001',  # Em quad
            '\u2002',  # En space
            '\u2003',  # Em space
            '\u2004',  # Three-per-em space
            '\u2005',  # Four-per-em space
            '\u2006',  # Six-per-em space
            '\u2007',  # Figure space
            '\u2008',  # Punctuation space
            '\u2009',  # Thin space
            '\u200a',  # Hair space
            '\u202f',  # Narrow no-break space
            '\u205f',  # Medium mathematical space
        ]
        for char in space_chars:
            text = text.replace(char, ' ')

        if self.preserve_paragraphs:
            # Preserve double newlines (paragraph breaks)
            text = re.sub(r'\n\n+', '\n\n', text)
            # Single newlines -> space (within paragraph)
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        else:
            # All newlines -> space
            text = re.sub(r'\n+', ' ', text)

        # Collapse multiple spaces
        text = re.sub(r' +', ' ', text)

        # Remove space before punctuation
        text = re.sub(r' +([.,;:!?])', r'\1', text)

        # Ensure space after punctuation
        text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)

        return text.strip()

    def _fix_char_confusions(self, text: str) -> str:
        """Fix common OCR character confusions."""
        # Process word by word to avoid false positives
        words = text.split()
        fixed_words = []

        for word in words:
            fixed_word = word

            # Only apply substitutions within words (not to numbers)
            if not word.isdigit():
                for wrong, right in self.CHAR_SUBSTITUTIONS.items():
                    # Don't fix if it's at word boundary
                    if wrong in fixed_word:
                        # Check if this looks like a word context
                        fixed_word = fixed_word.replace(wrong, right)

            # Fix l/1/I confusions in word context
            if re.match(r'^[A-Za-z]+$', fixed_word):
                # 1 in the middle of a word is likely l
                fixed_word = re.sub(r'(?<=[a-z])1(?=[a-z])', 'l', fixed_word)
                # | in word is likely l or I
                fixed_word = fixed_word.replace('|', 'l')

            fixed_words.append(fixed_word)

        return ' '.join(fixed_words)

    def _fix_common_words(self, text: str) -> str:
        """Fix known common OCR word errors."""
        # Case-insensitive word replacement
        for wrong, right in self.WORD_CORRECTIONS.items():
            # Match as whole word, preserve case
            pattern = r'\b' + wrong + r'\b'
            text = re.sub(pattern, right, text, flags=re.IGNORECASE)
            # Also try with first letter capitalized
            pattern = r'\b' + wrong.capitalize() + r'\b'
            text = re.sub(pattern, right.capitalize(), text)

        return text

    def _final_cleanup(self, text: str) -> str:
        """Final cleanup pass."""
        # Remove isolated single characters that are likely noise
        # (except common single-letter words: a, I)
        text = re.sub(r'\s[^aAiI\d]\s', ' ', text)

        # Remove repeated punctuation
        text = re.sub(r'([.,;:!?])\1+', r'\1', text)

        # Fix spacing around quotes
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r'\s+"', '"', text)

        # Remove leading/trailing whitespace from lines
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)

        # Remove empty lines
        text = re.sub(r'\n\n\n+', '\n\n', text)

        return text.strip()


class OCRPipeline:
    """
    Complete OCR pipeline with pre and post-processing.

    Usage:
        pipeline = OCRPipeline()

        # For images
        processed_image = pipeline.preprocess(pil_image)
        raw_text = pytesseract.image_to_string(processed_image)
        clean_text = pipeline.postprocess(raw_text)

        # Or all-in-one
        clean_text = pipeline.process_image(pil_image)
    """

    def __init__(
        self,
        preprocessor: Optional[OCRPreProcessor] = None,
        postprocessor: Optional[OCRPostProcessor] = None,
        tesseract_config: str = '--oem 3 --psm 6'
    ):
        """
        Initialize OCR pipeline.

        Args:
            preprocessor: Custom pre-processor (or None for default)
            postprocessor: Custom post-processor (or None for default)
            tesseract_config: Tesseract OCR configuration string
        """
        self.preprocessor = preprocessor or OCRPreProcessor()
        self.postprocessor = postprocessor or OCRPostProcessor()
        self.tesseract_config = tesseract_config

    def preprocess(self, image: Image.Image) -> Image.Image:
        """Apply pre-processing to image."""
        return self.preprocessor.process(image)

    def postprocess(self, text: str) -> str:
        """Apply post-processing to OCR text."""
        return self.postprocessor.process(text)

    def process_image(self, image: Image.Image) -> Tuple[str, dict]:
        """
        Complete OCR pipeline: preprocess -> OCR -> postprocess.

        Args:
            image: PIL Image to OCR

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        import pytesseract

        # Pre-process
        processed_image = self.preprocess(image)

        # OCR
        raw_text = pytesseract.image_to_string(
            processed_image,
            config=self.tesseract_config
        )

        # Post-process
        clean_text = self.postprocess(raw_text)

        # Metadata
        metadata = {
            'raw_length': len(raw_text),
            'clean_length': len(clean_text),
            'reduction_pct': round((1 - len(clean_text) / max(len(raw_text), 1)) * 100, 1),
            'preprocessing': OPENCV_AVAILABLE,
            'tesseract_config': self.tesseract_config
        }

        return clean_text, metadata


# Default pipeline instance
default_pipeline = OCRPipeline()


def preprocess_image(image: Image.Image) -> Image.Image:
    """Convenience function for image pre-processing."""
    return default_pipeline.preprocess(image)


def postprocess_text(text: str) -> str:
    """Convenience function for text post-processing."""
    return default_pipeline.postprocess(text)


def ocr_image(image: Image.Image) -> str:
    """Convenience function for complete OCR with pre/post processing."""
    text, _ = default_pipeline.process_image(image)
    return text

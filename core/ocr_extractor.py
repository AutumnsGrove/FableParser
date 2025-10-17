"""
OCR-based text extraction from screenshots.

This module handles extracting text from images using OCR (Optical Character Recognition),
which allows processing of arbitrarily large images without API size limits.
"""

import os
from typing import Optional
from pathlib import Path

import easyocr
from PIL import Image


class OCRExtractor:
    """
    OCR-based text extraction using EasyOCR.

    Attributes:
        reader: Initialized EasyOCR reader instance
        languages: List of languages to detect (default: ['en'])
    """

    def __init__(self, languages: Optional[list[str]] = None):
        """
        Initialize the OCR extractor.

        Args:
            languages: List of language codes to support (default: ['en'])
        """
        self.languages = languages or ['en']
        self.reader = None  # Lazy initialization

    def _ensure_reader_initialized(self):
        """Lazy initialization of EasyOCR reader to avoid slow startup."""
        if self.reader is None:
            print("🔍 Initializing OCR engine (first time only, may take a moment)...")
            # Enable GPU for faster processing (uses MPS on Mac M-series chips)
            self.reader = easyocr.Reader(self.languages, gpu=True)

    def extract_text(self, image_path: str, debug: bool = False) -> str:
        """
        Extract all text from an image using OCR.

        Args:
            image_path: Path to the image file
            debug: If True, save extracted text to a debug file

        Returns:
            Extracted text as a single string with newlines preserved

        Raises:
            FileNotFoundError: If the image file does not exist
            ValueError: If the image format is not supported

        Example:
            >>> extractor = OCRExtractor()
            >>> text = extractor.extract_text("screenshot.png")
            >>> print(text)
            "Finished\\n31 books\\nThe Way of Kings\\nBrandon Sanderson\\n..."
        """
        # Validate image exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Ensure reader is initialized
        self._ensure_reader_initialized()

        # Run OCR on the image - disable paragraph mode for better line-by-line extraction
        print(f"🔍 Running OCR on {os.path.basename(image_path)}...")
        results = self.reader.readtext(image_path, detail=1, paragraph=False)

        # Sort results by vertical position (top to bottom) for proper reading order
        # Each result is: (bounding_box, text, confidence)
        results_sorted = sorted(results, key=lambda x: x[0][0][1])  # Sort by top-left Y coordinate

        # Extract just the text from each result
        extracted_text = "\n".join([text for _, text, _ in results_sorted])

        print(f"✅ Extracted {len(extracted_text)} characters of text from {len(results_sorted)} text blocks")

        # Debug mode: save extracted text to file
        if debug:
            debug_file = str(Path(image_path).with_suffix('.ocr_debug.txt'))
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=== OCR EXTRACTED TEXT ===\n\n")
                f.write(extracted_text)
                f.write("\n\n=== DETAILED RESULTS ===\n\n")
                for i, (bbox, text, conf) in enumerate(results_sorted, 1):
                    f.write(f"{i}. [{conf:.2f}] {text}\n")
            print(f"📝 Debug info saved to {debug_file}")

        return extracted_text

    def preprocess_image(self, image_path: str, max_dimension: int = 4000) -> str:
        """
        Preprocess image by resizing if too large, to improve OCR speed.

        Args:
            image_path: Path to the original image
            max_dimension: Maximum allowed width or height in pixels

        Returns:
            Path to the processed image (original if no resize needed, temp file if resized)

        Example:
            >>> extractor = OCRExtractor()
            >>> processed_path = extractor.preprocess_image("huge_screenshot.png")
            >>> text = extractor.extract_text(processed_path)
        """
        img = Image.open(image_path)
        width, height = img.size

        # Check if image is too large
        if width <= max_dimension and height <= max_dimension:
            print(f"✅ Image size OK: {width}x{height}")
            return image_path

        # Calculate resize ratio to fit within max_dimension
        ratio = min(max_dimension / width, max_dimension / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)

        print(f"📐 Resizing image from {width}x{height} to {new_width}x{new_height}")

        # Resize with high-quality downsampling
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save to temporary file
        temp_path = str(Path(image_path).with_suffix('.processed.png'))
        resized.save(temp_path, 'PNG', optimize=True)

        print(f"✅ Saved preprocessed image to {temp_path}")
        return temp_path

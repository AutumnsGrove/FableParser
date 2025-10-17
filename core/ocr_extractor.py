"""
OCR-based text extraction from screenshots.

This module handles extracting text from images using OCR (Optical Character Recognition),
which allows processing of arbitrarily large images without API size limits.

Uses Tesseract 5 OCR with OpenCV preprocessing for optimal text detection.
"""

import os
from typing import Optional
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image


class OCRExtractor:
    """
    OCR-based text extraction using Tesseract 5.

    Attributes:
        languages: List of languages to detect (default: ['en'])
        tesseract_config: Custom Tesseract configuration for better accuracy
    """

    def __init__(self, languages: Optional[list[str]] = None):
        """
        Initialize the OCR extractor.

        Args:
            languages: List of language codes to support (default: ['en'])
        """
        self.languages = languages or ['en']
        # Tesseract config: PSM 6 (assume single uniform block of text)
        # --oem 3 (use both legacy and neural network OCR)
        self.tesseract_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=""'

    def _preprocess_image_cv2(self, image_path: str) -> np.ndarray:
        """
        Preprocess image with OpenCV for optimal OCR performance.

        Applies:
        1. Grayscale conversion
        2. OTSU thresholding for better text detection
        3. Optional denoising
        4. Optional deskewing

        Args:
            image_path: Path to the image file

        Returns:
            Preprocessed image as numpy array

        """
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply OTSU thresholding for binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Denoise the binary image
        denoised = cv2.medianBlur(binary, 3)

        # Optional: Apply morphological operations to improve text connectivity
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel, iterations=1)

        return processed

    def _get_text_with_confidence(self, image_array: np.ndarray) -> list[tuple[str, float]]:
        """
        Extract text from image with confidence scores using Tesseract.

        Args:
            image_array: Preprocessed image as numpy array

        Returns:
            List of tuples (text, confidence) for each detected line

        """
        # Use pytesseract to get detailed output
        data = pytesseract.image_to_data(
            image_array,
            config=self.tesseract_config,
            output_type=pytesseract.Output.DICT
        )

        text_with_conf = []

        # Process each detected word and group by line
        lines = {}
        for i, word in enumerate(data['text']):
            if word.strip():  # Skip empty words
                conf = int(data['conf'][i])
                if conf > 0:  # Only include words with positive confidence
                    line_num = data['line_num'][i]
                    if line_num not in lines:
                        lines[line_num] = {'text': [], 'confidences': []}
                    lines[line_num]['text'].append(word)
                    lines[line_num]['confidences'].append(conf)

        # Convert to line-by-line results with average confidence
        for line_num in sorted(lines.keys()):
            line_data = lines[line_num]
            line_text = ' '.join(line_data['text'])
            avg_confidence = np.mean(line_data['confidences']) / 100.0
            text_with_conf.append((line_text, avg_confidence))

        return text_with_conf

    def extract_text(self, image_path: str, debug: bool = False) -> str:
        """
        Extract all text from an image using OCR with Tesseract 5.

        Args:
            image_path: Path to the image file
            debug: If True, save extracted text to a debug file with confidence scores

        Returns:
            Extracted text as a single string with newlines preserved

        Raises:
            FileNotFoundError: If the image file does not exist
            ValueError: If the image format is not supported or OCR fails

        Example:
            >>> extractor = OCRExtractor()
            >>> text = extractor.extract_text("screenshot.png")
            >>> print(text)
            "Finished\\n31 books\\nThe Way of Kings\\nBrandon Sanderson\\n..."
        """
        # Validate image exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        print(f"🔍 Preprocessing image {os.path.basename(image_path)}...")
        try:
            # Preprocess image with OpenCV
            processed_img = self._preprocess_image_cv2(image_path)

            # Run OCR with Tesseract
            print(f"🔍 Running Tesseract OCR on {os.path.basename(image_path)}...")
            results_with_confidence = self._get_text_with_confidence(processed_img)

            # Results are already sorted top-to-bottom by line_num from Tesseract
            extracted_text = "\n".join([text for text, _ in results_with_confidence])

            print(f"✅ Extracted {len(extracted_text)} characters of text from {len(results_with_confidence)} lines")

            # Debug mode: save extracted text with confidence scores
            if debug:
                debug_file = str(Path(image_path).with_suffix('.ocr_debug.txt'))
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("=== OCR EXTRACTED TEXT ===\n\n")
                    f.write(extracted_text)
                    f.write("\n\n=== DETAILED RESULTS WITH CONFIDENCE ===\n\n")
                    for i, (text, conf) in enumerate(results_with_confidence, 1):
                        f.write(f"{i}. [{conf:.2%}] {text}\n")
                print(f"📝 Debug info saved to {debug_file}")

            return extracted_text

        except Exception as e:
            raise ValueError(f"OCR processing failed for {image_path}: {str(e)}") from e

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

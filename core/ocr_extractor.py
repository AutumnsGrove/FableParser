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
from PIL import Image, ImageFile

# Increase PIL's max image pixels limit to handle very large stitched screenshots
# Default is 89,478,485 pixels (~9000x9000). We'll increase to ~25000x25000
Image.MAX_IMAGE_PIXELS = 625_000_000

# Allow PIL to load truncated/damaged images (common with huge JPEGs)
ImageFile.LOAD_TRUNCATED_IMAGES = True


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
        # --oem 3 (use default OCR engine mode - LSTM only for better accuracy)
        self.tesseract_config = r'--oem 3 --psm 6'

    def _preprocess_image_cv2(self, image_path: str) -> np.ndarray:
        """
        Preprocess image with OpenCV for optimal OCR performance.

        Applies:
        1. Grayscale conversion
        2. Simple scaling/normalization
        3. Light denoising if needed

        Args:
            image_path: Path to the image file

        Returns:
            Preprocessed image as numpy array

        """
        try:
            print(f"🔍 Loading image with OpenCV...")
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image: {image_path}")

            print(f"✅ OpenCV successfully loaded image: shape={img.shape}")

            # Convert to grayscale
            print(f"🔍 Converting to grayscale...")
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # For dark mode screenshots, invert colors so text is black on white
            # Check if the image is dark mode by looking at average pixel value
            avg_brightness = np.mean(gray)
            print(f"📊 Average brightness: {avg_brightness:.1f} ({'dark mode' if avg_brightness < 127 else 'light mode'})")
            if avg_brightness < 127:  # Dark mode (dark background)
                print(f"🔄 Inverting colors for dark mode...")
                gray = cv2.bitwise_not(gray)  # Invert to make text black on white

            # Light denoising to reduce noise while preserving text clarity
            print(f"🔍 Applying denoising filter...")
            processed = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

            print(f"✅ Preprocessing complete")
            return processed

        except Exception as e:
            print(f"❌ OpenCV preprocessing failed: {type(e).__name__}: {str(e)}")
            raise

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

    def _load_image_robust(self, image_path: str):
        """
        Load image with multiple fallback strategies for corrupted/huge files.

        Returns: (numpy_array, width, height)
        """
        # Strategy 1: Try PIL with truncated image support
        print(f"🔍 Attempting to load with PIL (truncated image support enabled)...")
        try:
            pil_img = Image.open(image_path)
            width, height = pil_img.size
            print(f"📐 Image dimensions: {width}x{height}px")

            # Force load and convert
            pil_img.load()  # Force full load
            img_array = np.array(pil_img)
            pil_img.close()
            print(f"✅ PIL loaded successfully: {img_array.shape}")
            return img_array, width, height
        except Exception as e:
            print(f"⚠️  PIL failed: {e}")

        # Strategy 2: Try OpenCV
        print(f"🔍 Attempting to load with OpenCV...")
        try:
            img_array = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if img_array is not None:
                height, width = img_array.shape[:2]
                # Convert BGR to RGB for consistency
                img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
                print(f"✅ OpenCV loaded successfully: {img_array.shape}")
                return img_array, width, height
        except Exception as e:
            print(f"⚠️  OpenCV failed: {e}")

        # Strategy 3: Try converting JPEG to PNG first using imagemagick (if available)
        print(f"🔍 Attempting to repair image by converting to PNG...")
        try:
            import subprocess
            temp_png = str(Path(image_path).with_suffix('.repaired.png'))

            # Try using ImageMagick's convert command
            result = subprocess.run(
                ['magick', 'convert', image_path, temp_png],
                capture_output=True,
                timeout=60
            )

            if result.returncode == 0 and os.path.exists(temp_png):
                print(f"✅ Repaired image saved to {temp_png}")
                # Now try loading the repaired PNG
                pil_img = Image.open(temp_png)
                width, height = pil_img.size
                img_array = np.array(pil_img)
                pil_img.close()
                print(f"✅ Repaired image loaded: {img_array.shape}")
                return img_array, width, height
        except Exception as e:
            print(f"⚠️  Image repair failed: {e}")

        raise ValueError(f"All image loading strategies failed for {image_path}")

    def _convert_jpeg_to_png(self, image_path: str) -> str:
        """
        Convert JPEG to PNG using system tools for better compatibility.

        Returns: path to converted PNG file
        """
        # Skip if already PNG
        if image_path.lower().endswith('.png'):
            return image_path

        png_path = str(Path(image_path).with_suffix('.converted.png'))

        print(f"🔄 Attempting to convert JPEG to PNG for better compatibility...")

        # Strategy 1: Try macOS built-in sips command (very robust!)
        try:
            import subprocess
            print(f"🔍 Trying macOS sips command...")
            result = subprocess.run(
                ['sips', '-s', 'format', 'png', image_path, '--out', png_path],
                capture_output=True,
                timeout=120,
                text=True
            )

            if result.returncode == 0 and os.path.exists(png_path):
                # Verify the converted file
                test_img = Image.open(png_path)
                w, h = test_img.size
                test_img.close()
                print(f"✅ SIPS conversion successful: {w}x{h}px PNG created")
                return png_path
            else:
                print(f"⚠️  SIPS failed: {result.stderr}")
        except Exception as e:
            print(f"⚠️  SIPS conversion failed: {e}")

        # Strategy 2: Try ImageMagick if available
        try:
            import subprocess
            print(f"🔍 Trying ImageMagick convert...")
            result = subprocess.run(
                ['convert', image_path, png_path],
                capture_output=True,
                timeout=120,
                text=True
            )

            if result.returncode == 0 and os.path.exists(png_path):
                test_img = Image.open(png_path)
                w, h = test_img.size
                test_img.close()
                print(f"✅ ImageMagick conversion successful: {w}x{h}px PNG created")
                return png_path
            else:
                print(f"⚠️  ImageMagick failed: {result.stderr}")
        except Exception as e:
            print(f"⚠️  ImageMagick conversion failed: {e}")

        # Strategy 3: Use Python imageio (different JPEG decoder)
        try:
            import imageio.v3 as iio
            print(f"🔍 Trying imageio library...")
            img_data = iio.imread(image_path)
            iio.imwrite(png_path, img_data)

            if os.path.exists(png_path):
                test_img = Image.open(png_path)
                w, h = test_img.size
                test_img.close()
                print(f"✅ imageio conversion successful: {w}x{h}px PNG created")
                return png_path
        except ImportError:
            print(f"⚠️  imageio not installed")
        except Exception as e:
            print(f"⚠️  imageio conversion failed: {e}")

        # If all conversions fail, return original path and hope for the best
        print(f"⚠️  All conversion attempts failed, will try with original JPEG")
        return image_path

    def split_large_image(self, image_path: str, max_height: int = 8000) -> list[str]:
        """
        Split a very large image into horizontal bands for processing.

        This is necessary for extremely tall stitched screenshots that exceed
        PIL's processing limits when resizing.

        Uses multiple loading strategies for robust handling of corrupted/huge images.

        Args:
            image_path: Path to the large image
            max_height: Maximum height per chunk in pixels (default: 8000)

        Returns:
            List of paths to chunk image files (temp files that should be cleaned up)

        Example:
            >>> extractor = OCRExtractor()
            >>> chunks = extractor.split_large_image("huge_screenshot.png")
            >>> # chunks = ["huge_screenshot.chunk000.png", "huge_screenshot.chunk001.png", ...]
        """
        try:
            print(f"🔍 Checking if image needs splitting...")

            # First, try to convert JPEG to PNG if needed
            working_path = self._convert_jpeg_to_png(image_path)

            # Get dimensions
            with Image.open(working_path) as img:
                width, height = img.size

            print(f"📐 Image dimensions: {width}x{height}px")

            if height <= max_height:
                # No splitting needed
                print(f"✅ Image height ({height}px) is within limits, no splitting needed")
                return [working_path]

            # Calculate number of chunks needed
            num_chunks = (height + max_height - 1) // max_height  # Ceiling division

            print(f"✂️  Splitting {height}px tall image into {num_chunks} chunks of ~{max_height}px each...")

            # Load image with robust fallback strategies
            img_array, width, height = self._load_image_robust(working_path)

            chunk_paths = []

            print(f"🔍 Creating {num_chunks} chunk files...")
            for i in range(num_chunks):
                # Calculate boundaries for this chunk
                top = i * max_height
                bottom = min((i + 1) * max_height, height)
                chunk_height = bottom - top

                # Slice this chunk using numpy (super fast!)
                chunk_array = img_array[top:bottom, :, :]

                # Convert back to PIL Image for saving
                chunk_pil = Image.fromarray(chunk_array)

                # Save chunk to temp file (use working_path for naming)
                chunk_path = str(Path(working_path).with_suffix(f'.chunk{i:03d}.png'))
                chunk_pil.save(chunk_path, 'PNG')
                chunk_paths.append(chunk_path)

                print(f"  ✓ Chunk {i+1}/{num_chunks}: {width}x{chunk_height}px → {os.path.basename(chunk_path)}")

            # Release memory
            del img_array

            print(f"✅ Split complete: {num_chunks} chunks ready for OCR")
            return chunk_paths

        except Exception as e:
            print(f"❌ Image splitting failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def extract_text(self, image_path: str, debug: bool = False, return_chunks: bool = False) -> str | list[str]:
        """
        Extract all text from an image using OCR with Tesseract 5.

        Automatically handles very large images by splitting them into chunks.

        Args:
            image_path: Path to the image file
            debug: If True, save extracted text to a debug file with confidence scores
            return_chunks: If True, return a list of text strings (one per chunk) instead of combining

        Returns:
            If return_chunks=False (default): Extracted text as a single combined string
            If return_chunks=True: List of text strings, one per image chunk

        Raises:
            FileNotFoundError: If the image file does not exist
            ValueError: If the image format is not supported or OCR fails

        Example:
            >>> extractor = OCRExtractor()
            >>> text = extractor.extract_text("screenshot.png")
            >>> print(text)
            "Finished\\n31 books\\nThe Way of Kings\\nBrandon Sanderson\\n..."

            >>> # For chunked processing
            >>> chunks = extractor.extract_text("huge_screenshot.png", return_chunks=True)
            >>> print(len(chunks))  # Number of chunks
            9
        """
        # Validate image exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Check if image needs to be split into chunks
        chunk_paths = self.split_large_image(image_path, max_height=8000)
        need_cleanup = len(chunk_paths) > 1  # Clean up temp files if we split

        try:
            all_text = []

            # Process each chunk
            for chunk_idx, chunk_path in enumerate(chunk_paths, 1):
                if len(chunk_paths) > 1:
                    print(f"\n📄 Processing chunk {chunk_idx}/{len(chunk_paths)}...")

                print(f"🔍 Preprocessing image {os.path.basename(chunk_path)}...")
                # Preprocess image with OpenCV
                processed_img = self._preprocess_image_cv2(chunk_path)

                # Run OCR with Tesseract
                print(f"🔍 Running Tesseract OCR on {os.path.basename(chunk_path)}...")
                results_with_confidence = self._get_text_with_confidence(processed_img)

                # Results are already sorted top-to-bottom by line_num from Tesseract
                extracted_text = "\n".join([text for text, _ in results_with_confidence])

                print(f"✅ Extracted {len(extracted_text)} characters of text from {len(results_with_confidence)} lines")

                all_text.append(extracted_text)

                # Debug mode: save extracted text with confidence scores (per chunk)
                if debug:
                    debug_file = str(Path(chunk_path).with_suffix('.ocr_debug.txt'))
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write("=== OCR EXTRACTED TEXT ===\n\n")
                        f.write(extracted_text)
                        f.write("\n\n=== DETAILED RESULTS WITH CONFIDENCE ===\n\n")
                        for i, (text, conf) in enumerate(results_with_confidence, 1):
                            f.write(f"{i}. [{conf:.2%}] {text}\n")
                    print(f"📝 Debug info saved to {debug_file}")

            # Return chunks separately or combined based on parameter
            if return_chunks:
                # Return list of text strings for separate processing
                if len(chunk_paths) > 1:
                    print(f"\n✅ Returning {len(all_text)} text chunks for separate processing")
                return all_text
            else:
                # Combine all chunks into single string (original behavior)
                combined_text = "\n".join(all_text)
                if len(chunk_paths) > 1:
                    print(f"\n✅ Combined text from {len(chunk_paths)} chunks: {len(combined_text)} total characters")
                return combined_text

        except Exception as e:
            raise ValueError(f"OCR processing failed for {image_path}: {str(e)}") from e

        finally:
            # Clean up temporary chunk files
            if need_cleanup:
                print(f"\n🧹 Cleaning up {len(chunk_paths)} temporary chunk files...")
                for chunk_path in chunk_paths:
                    if chunk_path != image_path and os.path.exists(chunk_path):
                        try:
                            os.remove(chunk_path)
                            # Also remove debug files for chunks
                            debug_file = str(Path(chunk_path).with_suffix('.ocr_debug.txt'))
                            if os.path.exists(debug_file):
                                os.remove(debug_file)
                        except Exception as cleanup_error:
                            print(f"⚠️  Failed to clean up {chunk_path}: {cleanup_error}")
                print(f"✅ Cleanup complete")

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
        # Get file info first
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        print(f"📊 Image file size: {file_size_mb:.2f} MB")

        try:
            print(f"🔍 Attempting to open image with PIL...")
            img = Image.open(image_path)
            print(f"✅ PIL successfully opened the image")

            width, height = img.size
            print(f"📐 Image dimensions: {width}x{height} ({width*height:,} total pixels)")

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

        except Exception as e:
            print(f"❌ PIL failed to open image: {type(e).__name__}: {str(e)}")
            raise

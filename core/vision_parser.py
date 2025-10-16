"""
Screenshot analysis and book extraction using OCR + LLM text parsing.

This module handles the parsing of Fable app screenshots to extract
book lists with titles, authors, and reading status information.

Updated approach:
1. Use OCR to extract text from screenshot (handles large images)
2. Use LLM text analysis to parse and structure the book list
"""

import os
from typing import List, Dict, Any

from core.llm_inference import LLMInference
from core.ocr_extractor import OCRExtractor


# Text parsing prompt template for book extraction
TEXT_PARSING_PROMPT = """You are analyzing text extracted from a Fable reading app screenshot showing a list of books.

TASK:
Parse the extracted text to identify all books with their:
1. Title (exact as shown)
2. Author name (exact as shown)
3. Reading status (infer from context like shelf/list names)
   - Options: "read", "currently-reading", "want-to-read", "unknown"

CRITICAL INSTRUCTIONS:
- Look for patterns like:
  - Book titles followed by author names
  - Shelf/list indicators like "Finished", "Currently Reading", "Want to Read"
  - Page counts, dates, or other metadata (ignore these)
- Be precise with titles and authors - extract them exactly as they appear
- If a book appears partially, include it if both title and author are readable
- Return ONLY valid JSON - no markdown, no code blocks, no explanations
- Do NOT wrap the JSON in ```json``` code blocks
- Just return the raw JSON object

EXACT OUTPUT FORMAT (return this structure only):
{
  "books": [
    {
      "title": "The Way of Kings",
      "author": "Brandon Sanderson",
      "reading_status": "want-to-read"
    }
  ]
}
"""


def parse_screenshot(image_path: str, use_ocr: bool = True) -> List[Dict[str, Any]]:
    """
    Extract book list from Fable screenshot using OCR + LLM text parsing.

    This function uses a two-step approach:
    1. OCR to extract all text from the screenshot (handles arbitrarily large images)
    2. LLM text analysis to parse and structure the book list

    Args:
        image_path: Path to the screenshot image file
        use_ocr: Whether to use OCR approach (default: True). Set to False for legacy vision API.

    Returns:
        A list of book dictionaries, each containing:
            - title: The book title (str)
            - author: The author name (str)
            - reading_status: One of ["read", "currently-reading", "want-to-read", "unknown"]

    Example:
        [
            {
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "reading_status": "want-to-read"
            },
            {
                "title": "Project Hail Mary",
                "author": "Andy Weir",
                "reading_status": "read"
            }
        ]

    Raises:
        FileNotFoundError: If the image_path does not exist
        ValueError: If the LLM response cannot be parsed
    """
    # Validate image exists before processing
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Initialize LLM inference client
    try:
        llm = LLMInference()
    except (ValueError, FileNotFoundError) as e:
        raise ValueError(f"Failed to initialize LLM client: {e}")

    if use_ocr:
        # NEW APPROACH: OCR + Text Analysis
        # Step 1: Extract text using OCR
        try:
            ocr = OCRExtractor()
            # Preprocess image if needed (resize large images)
            processed_path = ocr.preprocess_image(image_path, max_dimension=4000)
            # Extract text from image
            extracted_text = ocr.extract_text(processed_path)

            # Clean up temporary file if created
            if processed_path != image_path and os.path.exists(processed_path):
                os.remove(processed_path)

        except Exception as e:
            raise ValueError(f"Failed to extract text from screenshot: {e}")

        # Step 2: Parse extracted text with LLM
        try:
            result = llm.analyze_text(extracted_text, TEXT_PARSING_PROMPT)
        except Exception as e:
            raise ValueError(f"Failed to parse extracted text: {e}")
    else:
        # LEGACY APPROACH: Vision API (kept for backwards compatibility)
        try:
            result = llm.analyze_screenshot(image_path, TEXT_PARSING_PROMPT)
        except Exception as e:
            raise ValueError(f"Failed to analyze screenshot: {e}")

    # Extract books list from response
    if "books" not in result:
        raise ValueError(
            "Invalid LLM response: missing 'books' key. "
            f"Response: {result.get('raw_response', 'No raw response available')}"
        )

    books = result["books"]

    # Validate that we got a list
    if not isinstance(books, list):
        raise ValueError(
            f"Invalid LLM response: 'books' should be a list, got {type(books).__name__}"
        )

    return books

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

FABLE APP TEXT LAYOUT PATTERN:
In Fable screenshots, each book entry follows this pattern:
1. Book Title (larger text)
2. Author Name, Translator (smaller text on the next line)
3. Optional metadata: page count, dates, etc.

EXAMPLE TEXT PATTERNS YOU'LL SEE:
```
Colorless Tsukuru Tazaki and His Years of Pilgrimage
Haruki Murakami, Philip Gabriel
400 pages    Jul 16, 2025 - Aug 25, 2...

The Martian
Andy Weir
369 pages
```

TASK:
Extract ALL books with:
1. **title**: Exact book title (first line of each entry)
2. **author**: Full author name (second line - ALWAYS present in Fable)
   - If you see a translator (after comma), include ONLY the primary author
   - Example: "Haruki Murakami, Philip Gabriel" → use "Haruki Murakami"
3. **reading_status**: Infer from shelf name
   - "Finished" → "read"
   - "Currently Reading" → "currently-reading"
   - "Want to Read" / other → "want-to-read"
4. **date_started**: Extract start date if visible (optional)
   - Format: "Jul 16, 2025" or "2025-07-16"
   - For finished books, this is the first date in "Jul 16, 2025 - Aug 25, 2..."
5. **date_finished**: Extract finish date if visible (optional)
   - Only for finished/read books
   - For finished books, this is the second date in "Jul 16, 2025 - Aug 25, 2..."
   - If year is cut off (e.g., "Jul 16, 2025 - Aug 25, 2..."), infer the year from date_started
   - Example: "Jul 16, 2025 - Aug 25, 2..." → date_finished should be "Aug 25, 2025"

CRITICAL RULES:
- **NEVER use "unknown" for author** - Fable ALWAYS shows the author name
- If author appears cut off or unclear, try to extract what's visible
- Look for the line IMMEDIATELY AFTER the title - that's the author
- Extract dates when visible (especially for finished books)
- Ignore page counts and other metadata (except dates)
- Be precise - extract names and dates exactly as shown

OUTPUT FORMAT (raw JSON only, no markdown):
{
  "books": [
    {
      "title": "Colorless Tsukuru Tazaki and His Years of Pilgrimage",
      "author": "Haruki Murakami",
      "reading_status": "read",
      "date_started": "Jul 16, 2025",
      "date_finished": "Aug 25, 2025"
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
        # NEW APPROACH: OCR + Text Analysis (with chunked processing)
        # Step 1: Extract text using OCR (handles splitting internally for large images)
        try:
            ocr = OCRExtractor()
            # Extract text from image and get chunks separately for large images
            # This automatically splits very large images into chunks if needed
            extracted_text = ocr.extract_text(image_path, debug=True, return_chunks=True)

            # Check if we got chunks (list) or single text (string)
            if isinstance(extracted_text, list):
                text_chunks = extracted_text
                print(f"📦 Processing {len(text_chunks)} text chunks separately through LLM...")
            else:
                # Single chunk, wrap in list
                text_chunks = [extracted_text]

        except Exception as e:
            raise ValueError(f"Failed to extract text from screenshot: {e}")

        # Step 2: Parse each text chunk with LLM separately to avoid overloading
        all_books = []
        for chunk_idx, chunk_text in enumerate(text_chunks, 1):
            if len(text_chunks) > 1:
                chars = len(chunk_text)
                print(f"  🔍 Chunk {chunk_idx}/{len(text_chunks)}: Sending {chars} characters to LLM...")

            try:
                result = llm.analyze_text(chunk_text, TEXT_PARSING_PROMPT)

                # Extract books from this chunk
                if "books" in result and isinstance(result["books"], list):
                    chunk_books = result["books"]
                    all_books.extend(chunk_books)
                    if len(text_chunks) > 1:
                        print(f"    ✓ Extracted {len(chunk_books)} books from chunk {chunk_idx}")
                else:
                    if len(text_chunks) > 1:
                        print(f"    ⚠️  No books found in chunk {chunk_idx}")

            except Exception as e:
                print(f"    ⚠️  LLM parsing failed for chunk {chunk_idx}: {e}")
                # Continue with other chunks even if one fails
                continue

        # Combine results from all chunks
        if len(text_chunks) > 1:
            print(f"✅ Combined {len(all_books)} total books from {len(text_chunks)} chunks")

        # Create result dict matching expected format
        result = {"books": all_books}
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

    # Post-processing: Clean up and validate book entries
    cleaned_books = []
    for book in books:
        # Ensure required fields exist
        if 'title' not in book:
            continue  # Skip books without titles

        # Clean up author field
        author = book.get('author', 'unknown').strip()

        # If author is unknown/empty, try to extract from title
        if author.lower() in ['unknown', 'n/a', 'none', '']:
            # Check if title contains "by [Author]" pattern
            title = book.get('title', '')
            if ' by ' in title.lower():
                parts = title.split(' by ', 1)
                book['title'] = parts[0].strip()
                book['author'] = parts[1].strip()
            else:
                # Keep as unknown if we can't extract
                book['author'] = 'unknown'
        else:
            # Clean up author: remove translator if present
            if ',' in author:
                author = author.split(',')[0].strip()
            book['author'] = author

        # Ensure reading_status exists
        if 'reading_status' not in book:
            book['reading_status'] = 'unknown'

        cleaned_books.append(book)

    return cleaned_books

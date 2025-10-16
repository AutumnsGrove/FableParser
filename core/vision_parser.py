"""
Screenshot analysis and book extraction using LLM vision capabilities.

This module handles the parsing of Fable app screenshots to extract
book lists with titles, authors, and reading status information.
"""

import os
from typing import List, Dict, Any

from core.llm_inference import LLMInference


# Vision prompt template for book extraction
VISION_PROMPT = """You are analyzing a screenshot from the Fable reading app showing a list of books.

TASK:
Extract all visible books with their:
1. Title (exact as shown)
2. Author name (exact as shown)
3. Reading status (infer from visual indicators like shelves/lists)
   - Options: "read", "currently-reading", "want-to-read", "unknown"

CRITICAL INSTRUCTIONS:
- Be precise with titles and authors
- If a book is partially visible, include it if title is readable
- Return ONLY valid JSON - no markdown, no code blocks, no explanations
- Do NOT wrap the JSON in ```json``` code blocks
- Just return the raw JSON object
- If you see shelf/list names like "Currently Reading" or "Want to Read", map to appropriate status

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


def parse_screenshot(image_path: str) -> List[Dict[str, Any]]:
    """
    Extract book list from Fable screenshot using LLM vision analysis.

    Args:
        image_path: Path to the screenshot image file

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

    # Analyze screenshot with vision model
    try:
        result = llm.analyze_screenshot(image_path, VISION_PROMPT)
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

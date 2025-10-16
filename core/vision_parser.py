"""
Screenshot analysis and book extraction using LLM vision capabilities.

This module handles the parsing of Fable app screenshots to extract
book lists with titles, authors, and reading status information.
"""

from typing import List, Dict, Any


# Vision prompt template for book extraction
VISION_PROMPT = """You are analyzing a screenshot from the Fable reading app showing a list of books.

TASK:
Extract all visible books with their:
1. Title (exact as shown)
2. Author name (exact as shown)
3. Reading status (infer from visual indicators like shelves/lists)
   - Options: "read", "currently-reading", "want-to-read", "unknown"

INSTRUCTIONS:
- Be precise with titles and authors
- If a book is partially visible, include it if title is readable
- Return structured JSON only
- If you see shelf/list names like "Want to Read", use that for status

OUTPUT FORMAT:
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
    # from core.llm_inference import LLMInference
    # llm = LLMInference()
    # result = llm.analyze_screenshot(image_path, VISION_PROMPT)
    # return result["books"]
    pass

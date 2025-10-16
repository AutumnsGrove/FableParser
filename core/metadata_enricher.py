"""
Open Library API integration for book metadata enrichment.

This module handles querying the Open Library API to fetch additional
metadata such as ISBN, cover images, publisher info, and page counts.
"""

from typing import Dict, Any, Optional
import requests
import urllib.parse
import logging

logger = logging.getLogger(__name__)


def enrich_book_metadata(book: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query Open Library API to enrich book metadata.

    This function searches for the book using title and author, then fetches
    additional metadata including ISBN, cover URLs, publisher, publication year,
    and page count from Open Library.

    Search priority:
    1. Search by title + author
    2. Get first matching edition
    3. Fetch ISBN, cover, pages, etc.

    Args:
        book: Dictionary containing at minimum:
            - title: Book title (str)
            - author: Author name (str)
            - reading_status: Reading status (str)

    Returns:
        Enriched book dictionary with original fields plus:
            - isbn: ISBN-13 (str, optional)
            - isbn_10: ISBN-10 (str, optional)
            - cover_url: Cover image URL (str, optional)
            - publisher: Publisher name (str, optional)
            - publish_year: Year published (int, optional)
            - pages: Number of pages (int, optional)
            - open_library_id: Open Library work ID (str, optional)

    Example:
        Input:
            {
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "reading_status": "want-to-read"
            }

        Output:
            {
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "reading_status": "want-to-read",
                "isbn": "9780765326355",
                "isbn_10": "0765326353",
                "cover_url": "https://covers.openlibrary.org/b/isbn/9780765326355-L.jpg",
                "publisher": "Tor Books",
                "publish_year": 2010,
                "pages": 1007,
                "open_library_id": "OL27214493M"
            }

    Raises:
        requests.exceptions.RequestException: If API request fails
        ValueError: If book data is invalid
    """
    # Create a copy to avoid modifying original dict
    enriched_book = book.copy()

    try:
        # Extract title and author, using default empty strings
        title = book.get('title', '')
        author = book.get('author', '')

        # Skip enrichment if no title or author
        if not title or not author:
            enriched_book['metadata_source'] = 'No title/author for enrichment'
            return enriched_book

        # Search Open Library
        result = _search_open_library(title, author)

        # If no result found, return original book with note
        if not result:
            enriched_book['metadata_source'] = 'No Open Library match'
            return enriched_book

        # Extract ISBNs
        isbns = result.get('isbn', [])

        # Separate ISBN-10 and ISBN-13
        isbn_10 = next((isbn for isbn in isbns if len(isbn) == 10), None)
        isbn_13 = next((isbn for isbn in isbns if len(isbn) == 13), None)

        # Use ISBN-13 as primary, fallback to first available ISBN
        primary_isbn = isbn_13 or isbn_10 or (isbns[0] if isbns else None)

        # Enrich book metadata
        enriched_book.update({
            'isbn': primary_isbn,
            'isbn_10': isbn_10,
            'cover_url': _get_cover_url(primary_isbn),
            'publisher': result.get('publisher', [None])[0] if result.get('publisher') else None,
            'publish_year': result.get('first_publish_year') or
                            (result.get('publish_year', [None])[0] if result.get('publish_year') else None),
            'pages': result.get('number_of_pages_median'),
            'open_library_id': result.get('key'),
            'metadata_source': 'Open Library'
        })

        # Remove None values to keep dict clean
        enriched_book = {k: v for k, v in enriched_book.items() if v is not None}

        return enriched_book

    except Exception as e:
        logger.error(f"Unexpected error enriching book metadata: {e}")
        enriched_book['metadata_source'] = 'Enrichment failed'
        return enriched_book


def _search_open_library(title: str, author: str) -> Optional[Dict[str, Any]]:
    """
    Search Open Library by title and author.

    Args:
        title: Book title
        author: Author name

    Returns:
        First matching book data from Open Library, or None if not found
    """
    try:
        # URL encode title and author
        encoded_title = urllib.parse.quote(title)
        encoded_author = urllib.parse.quote(author)

        # Construct API URL
        url = f"https://openlibrary.org/search.json?title={encoded_title}&author={encoded_author}"

        # Make request with timeout
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes

        # Parse JSON response
        data = response.json()

        # Return first result if available
        if data.get('docs') and len(data['docs']) > 0:
            return data['docs'][0]

        return None

    except requests.exceptions.RequestException as e:
        logger.warning(f"Open Library API request failed: {e}")
        return None


def _fetch_book_details(work_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed book information from Open Library.

    Args:
        work_id: Open Library work ID

    Returns:
        Detailed book metadata dictionary, or None if not found

    Note:
        This is a placeholder for future implementation.
        Currently, the search endpoint provides sufficient data.
    """
    return None


def _get_cover_url(isbn: Optional[str]) -> Optional[str]:
    """
    Get cover image URL from Open Library.

    Args:
        isbn: ISBN-13 or ISBN-10

    Returns:
        Cover image URL, or None if not available
    """
    if not isbn:
        return None

    # Open Library cover URL pattern
    cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    return cover_url

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

# Open Library API requires User-Agent header for regular use
# https://openlibrary.org/developers/api
HEADERS = {
    "User-Agent": "FableParser/1.0 (https://github.com/autumnsgrove/FableParser; autumnbrown23@pm.me)"
}


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

        # Extract work ID from search result
        work_id = result.get('key')

        # Initialize metadata variables
        isbn_13 = None
        isbn_10 = None
        publisher = None
        publish_date = None
        pages = None

        # Try to fetch edition details for more complete metadata
        if work_id:
            edition = _fetch_edition_details(work_id)
            if edition:
                # Extract ISBN-13 from edition
                isbn_13_list = edition.get('isbn_13', [])
                isbn_13 = isbn_13_list[0] if isbn_13_list else None

                # Extract ISBN-10 from edition
                isbn_10_list = edition.get('isbn_10', [])
                isbn_10 = isbn_10_list[0] if isbn_10_list else None

                # Extract publisher from edition
                publishers = edition.get('publishers', [])
                publisher = publishers[0] if publishers else None

                # Extract publish date from edition
                publish_date = edition.get('publish_date')

                # Extract page count from edition
                pages = edition.get('number_of_pages')

        # Fallback to search result if edition fetch failed
        if not isbn_13 and not isbn_10:
            isbns = result.get('isbn', [])
            isbn_10 = next((isbn for isbn in isbns if len(isbn) == 10), None)
            isbn_13 = next((isbn for isbn in isbns if len(isbn) == 13), None)

        if not publisher:
            publisher = result.get('publisher', [None])[0] if result.get('publisher') else None

        if not pages:
            pages = result.get('number_of_pages_median')

        # Use ISBN-13 as primary, fallback to ISBN-10
        primary_isbn = isbn_13 or isbn_10

        # Get cover URL - try ISBN first, then cover_i from search
        cover_url = _get_cover_url(primary_isbn)
        if not cover_url:
            cover_i = result.get('cover_i')
            if cover_i:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"

        # Parse publish year from publish_date if available
        publish_year = result.get('first_publish_year')
        if not publish_year and publish_date:
            # Try to extract year from publish_date string
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', str(publish_date))
            if year_match:
                publish_year = int(year_match.group())

        # Enrich book metadata
        enriched_book.update({
            'isbn': isbn_13,
            'isbn_10': isbn_10,
            'cover_url': cover_url,
            'publisher': publisher,
            'publish_year': publish_year,
            'pages': pages,
            'open_library_id': work_id,
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

        # Make request with timeout and required User-Agent header
        response = requests.get(url, headers=HEADERS, timeout=10)
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


def _fetch_edition_details(work_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch edition details from Open Library editions endpoint.

    Args:
        work_id: Open Library work ID (e.g., "/works/OL17267887W")

    Returns:
        Edition metadata with ISBN, publisher, pages, publish_date, or None if not found
    """
    try:
        # Construct editions API URL
        url = f"https://openlibrary.org{work_id}/editions.json"

        # Make request with timeout and required User-Agent header
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        # Parse JSON response
        data = response.json()

        # Get entries (editions list)
        editions = data.get('entries', [])

        if not editions:
            return None

        # Find the edition with the most complete metadata
        best_edition = None
        best_score = 0

        for edition in editions:
            # Score based on available fields
            score = 0
            if edition.get('isbn_13'):
                score += 3
            if edition.get('isbn_10'):
                score += 2
            if edition.get('publishers'):
                score += 2
            if edition.get('number_of_pages'):
                score += 2
            if edition.get('publish_date'):
                score += 1

            if score > best_score:
                best_score = score
                best_edition = edition

        return best_edition

    except requests.exceptions.RequestException as e:
        logger.warning(f"Open Library editions API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing edition details: {e}")
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

"""
Raindrop.io API integration for bookmark syncing.

This module handles syncing book markdown files to Raindrop.io
as bookmarks with metadata, tags, and cover images.
"""

import logging
from typing import Dict, Any, Optional

import requests

from utils import secrets_handler, config_handler

# Configure logging
logger = logging.getLogger(__name__)

# Raindrop.io API endpoint
RAINDROP_API_URL = "https://api.raindrop.io/rest/v1/raindrop"
REQUEST_TIMEOUT = 10  # seconds


def sync_to_raindrop(book: Dict[str, Any], markdown_path: str) -> str:
    """
    Sync book to Raindrop.io as a bookmark.

    Creates a bookmark in Raindrop.io with:
    - Link to Open Library page
    - Book title as bookmark title
    - Author and ISBN in excerpt
    - Configured tags from config.json
    - Cover image if available

    Args:
        book: Dictionary containing book metadata:
            - title: Book title (str, required)
            - author: Author name (str, required)
            - isbn: ISBN-13 (str, optional)
            - cover_url: Cover image URL (str, optional)
        markdown_path: Path to the generated markdown file

    Returns:
        Raindrop ID (str) of the created bookmark

    Example:
        >>> book = {
        ...     "title": "The Way of Kings",
        ...     "author": "Brandon Sanderson",
        ...     "isbn": "9780765326355",
        ...     "cover_url": "https://covers.openlibrary.org/..."
        ... }
        >>> raindrop_id = sync_to_raindrop(book, "/path/to/file.md")
        >>> print(raindrop_id)
        "12345678"

    Raises:
        ValueError: If Raindrop API token is not configured
        requests.exceptions.RequestException: If API request fails
    """
    # Check if API token is configured
    if not secrets_handler.has_key("raindrop_api_token"):
        raise ValueError(
            "Raindrop API token not configured. Please add 'raindrop_api_token' "
            "to your secrets.json file."
        )

    # Get API token
    api_token = secrets_handler.get_key("raindrop_api_token")

    # Build payload
    try:
        payload = _create_raindrop_payload(book)
    except Exception as e:
        logger.error(f"Failed to create Raindrop payload: {e}")
        raise

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    # Make API request
    try:
        logger.info(f"Syncing book '{book.get('title', 'Unknown')}' to Raindrop.io")
        response = requests.post(
            RAINDROP_API_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        # Extract raindrop ID from response
        response_data = response.json()
        raindrop_id = str(response_data["item"]["_id"])

        logger.info(f"Successfully created Raindrop bookmark with ID: {raindrop_id}")
        return raindrop_id

    except requests.exceptions.Timeout:
        logger.error("Raindrop API request timed out")
        raise requests.exceptions.RequestException(
            f"Request to Raindrop.io timed out after {REQUEST_TIMEOUT} seconds"
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"Raindrop API returned error: {e.response.status_code} - {e.response.text}")
        raise requests.exceptions.RequestException(
            f"Raindrop API error: {e.response.status_code} - {e.response.text}"
        )
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse Raindrop API response: {e}")
        raise requests.exceptions.RequestException(
            f"Invalid response from Raindrop API: {e}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while syncing to Raindrop: {e}")
        raise


def _create_raindrop_payload(book: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build request payload for Raindrop.io API.

    Args:
        book: Book metadata dictionary

    Returns:
        Dictionary formatted for Raindrop.io API request
    """
    # Get Open Library URL
    open_library_url = _get_open_library_url(book.get("isbn"))

    # Get configuration values
    collection_id = config_handler.get_config_value("raindrop.collection_id")
    default_tags = config_handler.get_config_value("raindrop.default_tags", ["books", "fable-import"])

    # Build excerpt with author and ISBN
    author = book.get("author", "Unknown Author")
    isbn = book.get("isbn", "N/A")
    excerpt = f"Author: {author} | ISBN: {isbn}"

    # Build base payload
    payload = {
        "link": open_library_url,
        "title": book.get("title", "Untitled Book"),
        "excerpt": excerpt,
        "tags": default_tags
    }

    # Add collection if configured
    if collection_id:
        payload["collection"] = {"$id": collection_id}

    # Add cover image if available
    cover_url = book.get("cover_url")
    if cover_url:
        payload["cover"] = cover_url

    logger.debug(f"Created Raindrop payload: {payload}")
    return payload


def _get_open_library_url(isbn: Optional[str]) -> str:
    """
    Generate Open Library URL from ISBN.

    Args:
        isbn: ISBN-13 or ISBN-10 (optional)

    Returns:
        Open Library URL string

    Raises:
        ValueError: If ISBN is not provided
    """
    if not isbn:
        raise ValueError(
            "ISBN is required to generate Open Library URL. "
            "Cannot sync book without ISBN."
        )

    # Clean ISBN (remove hyphens and spaces)
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    return f"https://openlibrary.org/isbn/{clean_isbn}"

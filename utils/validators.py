"""
Input validation functions for the Fable Parser.

This module provides validation functions for user inputs,
file paths, API responses, and data integrity checks.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import re
from urllib.parse import urlparse


def validate_image_file(image_path: str) -> bool:
    """
    Validate that a file exists and is a supported image format.

    Args:
        image_path: Path to image file

    Returns:
        True if valid, False otherwise

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file is not a supported image format
    """
    if not image_path:
        raise ValueError("Image path cannot be empty")

    path = Path(image_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Check if it's a file (not a directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {image_path}")

    # Validate supported image formats
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp'}
    file_extension = path.suffix.lower()

    if file_extension not in supported_formats:
        raise ValueError(
            f"Unsupported image format: {file_extension}. "
            f"Supported formats: {', '.join(supported_formats)}"
        )

    return True


def validate_book_data(book: Dict[str, Any]) -> bool:
    """
    Validate that book dictionary contains required fields.

    Required fields:
    - title (str, non-empty)
    - author (str, non-empty)
    - reading_status (str, one of valid statuses)

    Args:
        book: Book metadata dictionary

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if not isinstance(book, dict):
        raise ValueError("Book data must be a dictionary")

    # Check required fields exist
    required_fields = ['title', 'author', 'reading_status']
    missing_fields = [field for field in required_fields if field not in book]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {', '.join(missing_fields)}"
        )

    # Validate title
    if not isinstance(book['title'], str):
        raise ValueError("Title must be a string")
    if not book['title'].strip():
        raise ValueError("Title cannot be empty")

    # Validate author
    if not isinstance(book['author'], str):
        raise ValueError("Author must be a string")
    if not book['author'].strip():
        raise ValueError("Author cannot be empty")

    # Validate reading_status
    if not isinstance(book['reading_status'], str):
        raise ValueError("Reading status must be a string")
    if not validate_reading_status(book['reading_status']):
        raise ValueError(
            f"Invalid reading status: {book['reading_status']}. "
            f"Must be one of: read, currently-reading, want-to-read, unknown"
        )

    return True


def validate_isbn(isbn: str) -> bool:
    """
    Validate ISBN-10 or ISBN-13 format.

    Args:
        isbn: ISBN string to validate

    Returns:
        True if valid ISBN-10 or ISBN-13, False otherwise
    """
    # Handle None and empty strings
    if not isbn:
        return False

    if not isinstance(isbn, str):
        return False

    # Remove hyphens and spaces for validation
    clean_isbn = isbn.replace('-', '').replace(' ', '')

    # Check if it contains only digits (and possibly 'X' for ISBN-10)
    if not re.match(r'^[\dX]+$', clean_isbn):
        return False

    # Validate ISBN-10 (10 digits, last can be X)
    if len(clean_isbn) == 10:
        return _validate_isbn10(clean_isbn)

    # Validate ISBN-13 (13 digits)
    elif len(clean_isbn) == 13:
        return _validate_isbn13(clean_isbn)

    return False


def _validate_isbn10(isbn: str) -> bool:
    """Validate ISBN-10 checksum."""
    try:
        total = 0
        for i, char in enumerate(isbn[:-1]):
            total += int(char) * (10 - i)

        # Last character can be X (representing 10)
        if isbn[-1] == 'X':
            total += 10
        else:
            total += int(isbn[-1])

        return total % 11 == 0
    except (ValueError, IndexError):
        return False


def _validate_isbn13(isbn: str) -> bool:
    """Validate ISBN-13 checksum."""
    try:
        total = 0
        for i, char in enumerate(isbn):
            digit = int(char)
            if i % 2 == 0:
                total += digit
            else:
                total += digit * 3

        return total % 10 == 0
    except (ValueError, IndexError):
        return False


def validate_reading_status(status: str) -> bool:
    """
    Validate reading status value.

    Valid statuses: "read", "currently-reading", "want-to-read", "unknown"

    Args:
        status: Reading status string

    Returns:
        True if valid, False otherwise
    """
    if not status or not isinstance(status, str):
        return False

    valid_statuses = {
        'read',
        'currently-reading',
        'want-to-read',
        'unknown'
    }

    return status.lower() in valid_statuses


def validate_directory_path(path: str, create_if_missing: bool = False) -> bool:
    """
    Validate that a directory path exists and is writable.

    Args:
        path: Directory path to validate
        create_if_missing: If True, create directory if it doesn't exist

    Returns:
        True if valid and writable, False otherwise

    Raises:
        OSError: If directory cannot be created or is not writable
    """
    if not path:
        raise OSError("Directory path cannot be empty")

    dir_path = Path(path)

    # Create directory if requested and it doesn't exist
    if not dir_path.exists():
        if create_if_missing:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise OSError(f"Failed to create directory {path}: {e}")
        else:
            raise OSError(f"Directory does not exist: {path}")

    # Verify it's a directory
    if not dir_path.is_dir():
        raise OSError(f"Path exists but is not a directory: {path}")

    # Check if directory is writable
    if not os.access(dir_path, os.W_OK):
        raise OSError(f"Directory is not writable: {path}")

    return True


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        True if valid URL format, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        result = urlparse(url)
        # Check if scheme is http or https and netloc is present
        return all([
            result.scheme in ('http', 'https'),
            result.netloc
        ])
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename string
    """
    if not filename:
        return ""

    # Remove or replace invalid filesystem characters
    # Invalid chars: / \ : * ? " < > |
    invalid_chars = r'[/\\:*?"<>|]'
    sanitized = re.sub(invalid_chars, '', filename)

    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')

    # Ensure we don't end up with an empty string
    if not sanitized:
        sanitized = "unnamed_file"

    # Limit filename length (most filesystems support 255 chars)
    max_length = 255
    if len(sanitized) > max_length:
        # Try to preserve file extension if present
        name_parts = sanitized.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            # Reserve space for extension and dot
            max_name_length = max_length - len(ext) - 1
            sanitized = f"{name[:max_name_length]}.{ext}"
        else:
            sanitized = sanitized[:max_length]

    return sanitized


def validate_api_response(response: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that API response contains required fields.

    Args:
        response: API response dictionary
        required_fields: List of required field names

    Returns:
        True if all required fields present, False otherwise
    """
    if not isinstance(response, dict):
        return False

    if not isinstance(required_fields, list):
        return False

    # Check if all required fields are present in response
    return all(field in response for field in required_fields)

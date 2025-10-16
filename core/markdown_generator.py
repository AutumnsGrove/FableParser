"""
Markdown file generation with YAML frontmatter.

This module creates structured markdown files for each book with
YAML frontmatter containing metadata and formatted content sections.
"""

from typing import Dict, Any
import os
from datetime import datetime
from pathlib import Path
import yaml
from slugify import slugify

from utils.config_handler import get_output_directory, get_config_value


def generate_markdown_file(book: Dict[str, Any]) -> str:
    """
    Create markdown file with YAML frontmatter for a book.

    The file is saved to the output directory specified in config.json
    with a filename following the format: {author_last}_{title_slug}.md

    Args:
        book: Dictionary containing book metadata:
            - title: Book title (str, required)
            - author: Author name (str, required)
            - reading_status: Reading status (str, required)
            - isbn: ISBN-13 (str, optional)
            - isbn_10: ISBN-10 (str, optional)
            - cover_url: Cover image URL (str, optional)
            - publisher: Publisher name (str, optional)
            - publish_year: Year published (int, optional)
            - pages: Number of pages (int, optional)
            - open_library_id: Open Library work ID (str, optional)

    Returns:
        Absolute filepath of the created markdown file

    Example:
        Input:
            {
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "isbn": "9780765326355",
                "cover_url": "https://covers.openlibrary.org/...",
                "reading_status": "want-to-read"
            }

        Output:
            "/path/to/output/sanderson_way-of-kings.md"

    Raises:
        ValueError: If required fields (title, author) are missing
        OSError: If file cannot be written
    """
    # Validate required fields
    if not book.get("title"):
        raise ValueError("Book metadata must include 'title' field")
    if not book.get("author"):
        raise ValueError("Book metadata must include 'author' field")

    # Build file components
    frontmatter = _build_frontmatter(book)
    body = _build_markdown_body(book)
    filename = _generate_filename(book)

    # Get output directory and create if it doesn't exist
    output_dir = get_output_directory()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Build full file path
    filepath = os.path.join(output_dir, filename)

    # Write file with UTF-8 encoding
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            f.write('\n')
            f.write(body)
    except OSError as e:
        raise OSError(f"Failed to write markdown file to {filepath}: {e}")

    return os.path.abspath(filepath)


def _build_frontmatter(book: Dict[str, Any]) -> str:
    """
    Build YAML frontmatter section from book metadata.

    Args:
        book: Book metadata dictionary

    Returns:
        YAML frontmatter string (including --- delimiters)
    """
    # Get configured frontmatter fields
    frontmatter_fields = get_config_value("frontmatter_fields", [])

    # Build frontmatter dictionary with only configured fields
    frontmatter_data = {}
    for field in frontmatter_fields:
        if field in book:
            frontmatter_data[field] = book[field]

    # Add date_added if not present
    if "date_added" not in frontmatter_data:
        date_format = get_config_value("output.date_format", "%Y-%m-%d")
        frontmatter_data["date_added"] = datetime.now().strftime(date_format)

    # Add source if not present
    if "source" not in frontmatter_data:
        frontmatter_data["source"] = "fable"

    # Convert to YAML and wrap with delimiters
    yaml_content = yaml.dump(
        frontmatter_data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )

    return f"---\n{yaml_content}---"


def _build_markdown_body(book: Dict[str, Any]) -> str:
    """
    Build markdown body content for the book file.

    Args:
        book: Book metadata dictionary

    Returns:
        Formatted markdown content string
    """
    sections = []

    # Title header
    sections.append(f"# {book['title']}")
    sections.append("")

    # Basic information
    info_lines = []
    if book.get("author"):
        info_lines.append(f"**Author:** {book['author']}")

    if book.get("isbn"):
        info_lines.append(f"**ISBN-13:** {book['isbn']}")
    elif book.get("isbn_10"):
        info_lines.append(f"**ISBN-10:** {book['isbn_10']}")

    # Publisher and year
    publisher_info = []
    if book.get("publisher"):
        publisher_info.append(book["publisher"])
    if book.get("publish_year"):
        publisher_info.append(f"({book['publish_year']})")

    if publisher_info:
        info_lines.append(f"**Publisher:** {' '.join(publisher_info)}")

    if info_lines:
        sections.extend(info_lines)
        sections.append("")

    # Cover image
    if book.get("cover_url"):
        sections.append(f"![Book Cover]({book['cover_url']})")
        sections.append("")

    # Reading status section
    reading_status = book.get("reading_status", "").lower()
    status_emoji_map = {
        "want-to-read": "📚 Want to Read",
        "currently-reading": "📖 Currently Reading",
        "read": "✅ Read"
    }

    status_display = status_emoji_map.get(
        reading_status,
        f"📚 {reading_status.replace('-', ' ').title()}"
    )

    sections.append("## Reading Status")
    sections.append(status_display)
    sections.append("")

    # Links section
    links = []
    if book.get("isbn"):
        links.append(f"- [Open Library](https://openlibrary.org/isbn/{book['isbn']})")
    elif book.get("isbn_10"):
        links.append(f"- [Open Library](https://openlibrary.org/isbn/{book['isbn_10']})")

    if book.get("open_library_id"):
        links.append(f"- [Open Library Work](https://openlibrary.org{book['open_library_id']})")

    if links:
        sections.append("## Links")
        sections.extend(links)
        sections.append("")

    # Footer
    sections.append("---")
    sections.append("")
    today = datetime.now().strftime("%B %d, %Y")
    sections.append(f"*Imported from Fable on {today}*")

    return "\n".join(sections)


def _generate_filename(book: Dict[str, Any]) -> str:
    """
    Generate filename from book metadata.

    Uses format: {author_last}_{title_slug}.md

    Args:
        book: Book metadata dictionary

    Returns:
        Sanitized filename string
    """
    # Get filename format from config
    filename_format = get_config_value(
        "output.filename_format",
        "{author_last}_{title_slug}"
    )

    # Extract author last name
    author = book.get("author", "unknown")
    author_parts = author.split()
    author_last = author_parts[-1] if author_parts else "unknown"

    # Create slugs
    author_last_slug = _slugify_text(author_last)
    title_slug = _slugify_text(book.get("title", "untitled"))

    # Format filename
    filename = filename_format.format(
        author_last=author_last_slug,
        title_slug=title_slug
    )

    # Ensure .md extension
    if not filename.endswith(".md"):
        filename += ".md"

    return filename


def _slugify_text(text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text (lowercase, hyphens, no special chars)
    """
    return slugify(text, lowercase=True)

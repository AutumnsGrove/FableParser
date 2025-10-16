"""
Obsidian vault filesystem sync operations.

This module handles copying generated markdown files to an
Obsidian vault directory as specified in config.json.
"""

from typing import Optional
import os
import shutil
from pathlib import Path

from utils import config_handler


def sync_to_obsidian(markdown_path: str) -> bool:
    """
    Copy markdown file to Obsidian vault.

    Copies the generated markdown file to the Obsidian vault directory
    specified in config.json under obsidian.vault_path.

    Args:
        markdown_path: Path to the markdown file to copy

    Returns:
        True if copy succeeded, False otherwise

    Example:
        >>> success = sync_to_obsidian("/path/to/output/book.md")
        >>> print(success)
        True

    Raises:
        FileNotFoundError: If markdown_path does not exist
        ValueError: If Obsidian vault path is not configured
        OSError: If file copy fails
    """
    # Check if markdown file exists
    if not os.path.exists(markdown_path):
        raise FileNotFoundError(
            f"Markdown file not found: {markdown_path}"
        )

    # Get vault path from config
    vault_path = config_handler.get_config_value("obsidian.vault_path")

    if not vault_path:
        raise ValueError(
            "Obsidian vault path is not configured in config.json. "
            "Please set 'obsidian.vault_path' in your configuration."
        )

    # Validate vault path
    _validate_vault_path(vault_path)

    # Get filename from markdown_path (just the basename)
    filename = os.path.basename(markdown_path)

    # Build destination path
    destination_path = os.path.join(vault_path, filename)

    try:
        # Copy file preserving metadata
        shutil.copy2(markdown_path, destination_path)
        return True
    except OSError as e:
        raise OSError(
            f"Failed to copy file to Obsidian vault: {e}"
        )


def _validate_vault_path(vault_path: str) -> bool:
    """
    Validate that the Obsidian vault path exists and is writable.

    Args:
        vault_path: Path to Obsidian vault directory

    Returns:
        True if valid, False otherwise

    Raises:
        OSError: If path is invalid, not a directory, or not writable
    """
    path = Path(vault_path)

    # Check if path exists
    if not path.exists():
        raise OSError(
            f"Obsidian vault path does not exist: {vault_path}"
        )

    # Check if it's a directory
    if not path.is_dir():
        raise OSError(
            f"Obsidian vault path is not a directory: {vault_path}"
        )

    # Check if it's writable
    if not os.access(vault_path, os.W_OK):
        raise OSError(
            f"Obsidian vault path is not writable: {vault_path}"
        )

    return True


def _create_index_file(vault_path: str, books: list) -> Optional[str]:
    """
    Create an index file of all imported books in the Obsidian vault.

    This is an optional feature controlled by config.json (obsidian.create_index).

    Args:
        vault_path: Path to Obsidian vault directory
        books: List of book metadata dictionaries

    Returns:
        Path to created index file, or None if disabled
    """
    # Future: Create index of all imported books
    return None

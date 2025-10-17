#!/usr/bin/env python3
"""
Script to rename existing markdown files to new filename format.

Reads existing markdown files in the output directory and renames them
from the old format (author_last_title_slug.md) to the new format
(FirstInitialLastName--TitleInCamelCase.md) without regenerating content.
"""

import os
import re
from pathlib import Path
import yaml

from utils.config_handler import get_output_directory


def to_camel_case(text: str) -> str:
    """
    Convert text to CamelCase (PascalCase) for filenames.

    This is the same function used in markdown_generator.py
    """
    # Replace common separators with spaces
    text = text.replace('-', ' ').replace('_', ' ')

    # Remove possessive apostrophes and other punctuation
    text = re.sub(r"'s\b", 's', text)  # "Author's" -> "Authors"
    text = re.sub(r"[^\w\s]", '', text)  # Remove remaining punctuation

    # Split into words and capitalize each
    words = text.split()
    camel_words = [word.capitalize() for word in words if word]

    return ''.join(camel_words)


def generate_new_filename(author: str, title: str) -> str:
    """
    Generate new filename from author and title.

    This is the same logic used in markdown_generator.py
    """
    # Extract author name parts
    author_parts = author.split()

    if len(author_parts) == 0:
        # No author name
        author_prefix = "Unknown"
    elif len(author_parts) == 1:
        # Only one name (could be first or last)
        author_prefix = author_parts[0].capitalize()
    else:
        # Multiple parts: use first initial + last name
        first_initial = author_parts[0][0].upper()
        last_name = author_parts[-1].capitalize()
        author_prefix = f"{first_initial}{last_name}"

    # Convert title to CamelCase
    title_camel = to_camel_case(title)

    # Combine with double dash separator
    filename = f"{author_prefix}--{title_camel}.md"

    return filename


def extract_metadata_from_file(filepath: str) -> dict:
    """
    Extract author and title from markdown file frontmatter.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for YAML frontmatter
        if not content.startswith('---'):
            print(f"  ⚠️  No frontmatter found, skipping")
            return None

        # Find the end of frontmatter
        end_idx = content.find('---', 3)
        if end_idx == -1:
            print(f"  ⚠️  Malformed frontmatter, skipping")
            return None

        # Parse YAML
        yaml_content = content[4:end_idx].strip()
        metadata = yaml.safe_load(yaml_content)

        if not isinstance(metadata, dict):
            print(f"  ⚠️  Invalid frontmatter, skipping")
            return None

        # Check for required fields
        if 'author' not in metadata or 'title' not in metadata:
            print(f"  ⚠️  Missing author or title in frontmatter, skipping")
            return None

        return metadata

    except Exception as e:
        print(f"  ⚠️  Error reading file: {e}")
        return None


def rename_files_in_directory(directory: str, dry_run: bool = True):
    """
    Rename all markdown files in the directory to the new format.

    Args:
        directory: Path to directory containing markdown files
        dry_run: If True, only print what would be renamed without actually renaming
    """
    # Find all .md files
    md_files = list(Path(directory).glob("*.md"))

    if not md_files:
        print(f"No markdown files found in {directory}")
        return

    print(f"Found {len(md_files)} markdown files in {directory}\n")

    renamed_count = 0
    skipped_count = 0
    error_count = 0

    for filepath in md_files:
        old_filename = filepath.name
        print(f"Processing: {old_filename}")

        # Extract metadata
        metadata = extract_metadata_from_file(str(filepath))
        if not metadata:
            skipped_count += 1
            continue

        # Generate new filename
        author = metadata.get('author', 'Unknown')
        title = metadata.get('title', 'Untitled')
        new_filename = generate_new_filename(author, title)

        # Check if filename would change
        if old_filename == new_filename:
            print(f"  ✓ Already using new format: {new_filename}\n")
            skipped_count += 1
            continue

        # Show what will be renamed
        print(f"  Old: {old_filename}")
        print(f"  New: {new_filename}")

        # Check if target file already exists
        new_filepath = filepath.parent / new_filename
        if new_filepath.exists() and new_filepath != filepath:
            print(f"  ⚠️  WARNING: Target file already exists! Skipping to avoid overwrite.\n")
            error_count += 1
            continue

        # Perform rename (if not dry run)
        if dry_run:
            print(f"  [DRY RUN] Would rename\n")
            renamed_count += 1
        else:
            try:
                filepath.rename(new_filepath)
                print(f"  ✓ Renamed successfully\n")
                renamed_count += 1
            except Exception as e:
                print(f"  ❌ Error renaming: {e}\n")
                error_count += 1

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files: {len(md_files)}")
    print(f"{'Would rename' if dry_run else 'Renamed'}: {renamed_count}")
    print(f"Skipped (already correct or no metadata): {skipped_count}")
    print(f"Errors: {error_count}")

    if dry_run:
        print("\n💡 This was a dry run. Run with --execute to actually rename files.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Rename markdown files to new filename format'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually rename files (default is dry-run mode)'
    )
    parser.add_argument(
        '--directory',
        type=str,
        default=None,
        help='Directory containing markdown files (default: output directory from config)'
    )

    args = parser.parse_args()

    # Get directory
    directory = args.directory if args.directory else get_output_directory()

    print("=" * 60)
    print("MARKDOWN FILE RENAMER")
    print("=" * 60)
    print(f"Directory: {directory}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("=" * 60)
    print()

    # Confirm if executing
    if args.execute:
        response = input("⚠️  This will rename files. Continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
        print()

    # Run the rename operation
    rename_files_in_directory(directory, dry_run=not args.execute)


if __name__ == "__main__":
    main()

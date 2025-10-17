#!/usr/bin/env python3
"""
Metadata Refresh Tool - Gradio UI for updating existing markdown files with complete OpenLibrary metadata.

This tool reads an existing markdown file, searches OpenLibrary for the most complete data,
and updates the file with enriched metadata (fixing truncated titles, adding missing fields, etc).
"""

import gradio as gr
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple

from core import metadata_enricher, markdown_generator
from utils.config_handler import get_output_directory


def extract_book_from_file(file_path: str) -> Dict[str, Any]:
    """
    Extract book metadata from an existing markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary of book metadata from frontmatter
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract YAML frontmatter
        if not content.startswith('---'):
            raise ValueError("No YAML frontmatter found in file")

        end_idx = content.find('---', 3)
        if end_idx == -1:
            raise ValueError("Malformed YAML frontmatter")

        yaml_content = content[4:end_idx].strip()
        metadata = yaml.safe_load(yaml_content)

        if not isinstance(metadata, dict):
            raise ValueError("Invalid frontmatter format")

        return metadata

    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")


def format_metadata_display(book: Dict[str, Any]) -> str:
    """
    Format book metadata for display.
    """
    lines = []
    lines.append("**Title:** " + str(book.get('title', 'N/A')))
    lines.append("**Author:** " + str(book.get('author', 'N/A')))

    if book.get('isbn'):
        lines.append("**ISBN-13:** " + book['isbn'])
    elif book.get('isbn_10'):
        lines.append("**ISBN-10:** " + book['isbn_10'])

    if book.get('publisher'):
        pub_str = book['publisher']
        if book.get('publish_year'):
            pub_str += f" ({book['publish_year']})"
        lines.append("**Publisher:** " + pub_str)

    if book.get('pages'):
        lines.append("**Pages:** " + str(book['pages']))

    if book.get('cover_url'):
        lines.append("**Cover:** ✅ Available")
    else:
        lines.append("**Cover:** ❌ Missing")

    if book.get('open_library_id'):
        lines.append("**OpenLibrary ID:** " + book['open_library_id'])

    return "\n".join(lines)


def refresh_file_metadata(file_path: str) -> Tuple[str, str, str]:
    """
    Refresh metadata for a markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (status_message, before_metadata, after_metadata)
    """
    log = []

    try:
        # Step 1: Read existing file
        log.append("📖 Reading existing file...")
        existing_book = extract_book_from_file(file_path)

        # Format before metadata
        before_display = format_metadata_display(existing_book)
        log.append(f"✅ Found: {existing_book.get('title', 'Unknown')}")
        log.append("")

        # Step 2: Enrich with OpenLibrary
        log.append("🔍 Searching OpenLibrary for complete metadata...")

        # Define callback for progress
        def search_progress(msg: str):
            log.append(f"  {msg}")

        enriched_book = metadata_enricher.enrich_book_metadata(
            existing_book,
            progress_callback=search_progress
        )

        # Format after metadata
        after_display = format_metadata_display(enriched_book)

        # Step 3: Check if we got improvements
        improvements = []

        # Check for title improvement (fix truncation)
        old_title = existing_book.get('title', '')
        new_title = enriched_book.get('title', '')
        if new_title and (len(new_title) > len(old_title) or '...' in old_title):
            improvements.append(f"✨ Title expanded: '{old_title}' → '{new_title}'")

        # Check for new fields
        for field in ['isbn', 'isbn_10', 'cover_url', 'publisher', 'pages', 'open_library_id']:
            if enriched_book.get(field) and not existing_book.get(field):
                improvements.append(f"✨ Added {field}")

        if improvements:
            log.append("")
            log.append("📊 Improvements found:")
            log.extend([f"  {imp}" for imp in improvements])
        else:
            log.append("")
            log.append("ℹ️  No additional metadata found - file is already complete!")

        log.append("")
        log.append("💾 Updating file with enriched metadata...")

        # Step 4: Regenerate the file
        new_filepath = markdown_generator.generate_markdown_file(enriched_book)

        log.append(f"✅ File updated: {os.path.basename(new_filepath)}")
        log.append("")
        log.append("🎉 Done!")

        return "\n".join(log), before_display, after_display

    except Exception as e:
        log.append(f"❌ Error: {str(e)}")
        return "\n".join(log), "Error reading file", ""


def create_interface() -> gr.Blocks:
    """
    Create Gradio interface for metadata refresh tool.
    """
    with gr.Blocks(title="Metadata Refresh Tool") as app:
        gr.Markdown("# 🔄 Metadata Refresh Tool")
        gr.Markdown("Upload an existing markdown file to enrich it with complete OpenLibrary metadata")

        with gr.Row():
            with gr.Column():
                file_input = gr.File(
                    label="Upload Markdown File",
                    file_types=[".md"],
                    type="filepath"
                )

                refresh_btn = gr.Button("🔄 Refresh Metadata", variant="primary", size="lg")

                gr.Markdown("### Use this tool to:")
                gr.Markdown("- Fix truncated titles")
                gr.Markdown("- Add missing ISBN/cover/publisher data")
                gr.Markdown("- Enrich old files with new OpenLibrary data")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📋 Before")
                before_output = gr.Markdown("*Upload a file to see metadata*")

            with gr.Column():
                gr.Markdown("### ✨ After")
                after_output = gr.Markdown("*Refreshed metadata will appear here*")

        status_output = gr.Textbox(
            label="Processing Status",
            lines=15,
            interactive=False
        )

        # Connect the refresh function
        refresh_btn.click(
            fn=refresh_file_metadata,
            inputs=[file_input],
            outputs=[status_output, before_output, after_output]
        )

    return app


def main():
    """
    Main entry point for the metadata refresh tool.
    """
    app = create_interface()
    app.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7861  # Different port from main app
    )


if __name__ == "__main__":
    main()

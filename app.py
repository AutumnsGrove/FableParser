"""
Gradio web interface for Fable Screenshot Parser.

This is the main entry point for the application, providing a web-based
interface for uploading screenshots and processing book lists.
"""

import gradio as gr
from typing import Tuple, List
import os
import yaml
from pathlib import Path

from core import vision_parser, metadata_enricher
from core import markdown_generator, raindrop_sync, obsidian_sync
from utils import config_handler


def _check_existing_file(book):
    """Check if a markdown file already exists for this book and load its metadata."""
    from core.markdown_generator import _generate_filename
    from utils.config_handler import get_output_directory

    try:
        filename = _generate_filename(book)
        output_dir = get_output_directory()
        filepath = os.path.join(output_dir, filename)

        if os.path.exists(filepath):
            # File exists, load existing metadata
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract frontmatter
            if content.startswith('---'):
                end_idx = content.find('---', 3)
                if end_idx != -1:
                    yaml_content = content[4:end_idx].strip()
                    existing_data = yaml.safe_load(yaml_content)
                    if isinstance(existing_data, dict):
                        # Merge existing metadata with book data
                        merged = book.copy()
                        merged.update(existing_data)
                        return merged, filepath

        return None, None
    except Exception:
        return None, None


def process_pipeline(
    image_path: str,
    sync_raindrop: bool,
    sync_obsidian: bool,
    progress=gr.Progress()
) -> Tuple[str, List[str]]:
    """
    Main processing pipeline for converting screenshots to markdown files.

    This function orchestrates the complete workflow:
    1. Analyze screenshot using vision parser (0% → 20%)
    2. Enrich each book with Open Library metadata (20% → 60%)
    3. Generate markdown files (60% → 100%)
    4. Optionally sync to Raindrop.io
    5. Optionally copy to Obsidian vault

    Args:
        image_path: Path to uploaded screenshot image
        sync_raindrop: Whether to sync books to Raindrop.io
        sync_obsidian: Whether to copy files to Obsidian vault
        progress: Gradio Progress object for UI progress bar updates

    Returns:
        Tuple of (status_log, list_of_file_paths):
            - status_log: Multi-line string with processing status updates
            - list_of_file_paths: List of generated markdown file paths

    Example:
        >>> log, files = process_pipeline("/path/to/screenshot.png", False, False)
        >>> print(log)
        "Found 5 books\\n Processing 1/5: The Way of Kings\\n..."
        >>> print(files)
        ["/path/to/output/sanderson_way-of-kings.md", ...]
    """
    log = []
    files = []

    try:
        # Phase 1: Vision Analysis (0% → 20%)
        progress(0.0, desc="📸 Analyzing screenshot...")
        log.append("📸 Analyzing screenshot...")

        books = vision_parser.parse_screenshot(image_path)
        progress(0.2, desc=f"✅ Found {len(books)} books")
        log.append(f"✅ Found {len(books)} books")

        # Debug: Show what we got
        if len(books) == 0:
            log.append("⚠️  Warning: No books were extracted from the screenshot")
            log.append("This might be due to:")
            log.append("  - Unclear image quality")
            log.append("  - Unexpected screenshot format")
            log.append("  - JSON parsing issues")
            return "\n".join(log), []

        log.append("")  # Blank line for readability

        # Phase 2: Sequential metadata enrichment (20% → 60%)
        progress(0.2, desc=f"🔍 Enriching metadata for {len(books)} books...")
        log.append(f"🔍 Enriching metadata for {len(books)} books sequentially...")

        # Filter out books without required fields
        valid_books = []
        for i, book in enumerate(books, 1):
            if 'title' not in book:
                log.append(f"⚠️  Skipping book {i}: missing 'title' field")
            else:
                valid_books.append((i, book))

        if not valid_books:
            log.append("❌ No valid books to process")
            progress(1.0, desc="❌ No valid books to process")
            return "\n".join(log), []

        # Enrich all books sequentially to respect API rate limits
        enriched_books = []
        total_books = len(valid_books)

        for completed_enrichments, (idx, book) in enumerate(valid_books, 1):
            try:
                # Check if file already exists before making API calls
                existing_data, existing_path = _check_existing_file(book)

                if existing_data:
                    # Use existing metadata from file
                    enriched_books.append((idx, existing_data))
                    log.append(f"  ⏭️  Skipped: {book.get('title', 'Unknown')} (already exists)")
                else:
                    # Define callback to capture search progress messages
                    def search_progress(msg: str):
                        log.append(f"    {msg}")

                    enriched = metadata_enricher.enrich_book_metadata(book, progress_callback=search_progress)
                    enriched_books.append((idx, enriched))
                    log.append(f"  ✓ Enriched: {enriched.get('title', 'Unknown')}")
            except Exception as e:
                log.append(f"  ⚠️  Failed to enrich book {idx}: {str(e)}")
                # Use original book data if enrichment fails
                enriched_books.append((idx, book))

            # Update progress: 20% + (40% × completed/total)
            progress_pct = 0.2 + (0.4 * completed_enrichments / total_books)
            progress(progress_pct, desc=f"🔍 Enriching metadata ({completed_enrichments}/{total_books} books)")
        progress(0.6, desc="✅ Metadata enrichment complete")
        log.append(f"✅ Metadata enrichment complete\n")

        # Phase 3: Generate markdown files and sync (60% → 100%)
        total_books_to_process = len(enriched_books)

        for book_num, (idx, enriched) in enumerate(enriched_books, 1):
            # Calculate base progress for this book: 60% + (40% × book_num/total)
            base_progress = 0.6 + (0.4 * (book_num - 1) / total_books_to_process)
            book_progress_range = 0.4 / total_books_to_process  # How much progress this book represents

            progress(base_progress, desc=f"📖 Processing {book_num}/{total_books_to_process}: {enriched.get('title', 'Unknown')}")
            log.append(f"📖 Processing {idx}/{len(books)}: {enriched.get('title', 'Unknown')}")

            # Generate markdown (33% of this book's progress)
            filepath = markdown_generator.generate_markdown_file(enriched)
            files.append(filepath)
            log.append(f"  ✓ Created {os.path.basename(filepath)}")
            progress(base_progress + book_progress_range * 0.33, desc=f"📖 Processing {book_num}/{total_books_to_process}: Generated markdown")

            # Optional syncs
            if sync_raindrop and config_handler.get_config_value("raindrop.enabled"):
                rd_id = raindrop_sync.sync_to_raindrop(enriched, filepath)
                log.append(f"  ☁️  Synced to Raindrop (ID: {rd_id})")
                progress(base_progress + book_progress_range * 0.66, desc=f"📖 Processing {book_num}/{total_books_to_process}: Synced to Raindrop")

            if sync_obsidian and config_handler.get_config_value("obsidian.enabled"):
                obsidian_sync.sync_to_obsidian(filepath)
                log.append(f"  📝 Copied to Obsidian vault")
                progress(base_progress + book_progress_range * 0.9, desc=f"📖 Processing {book_num}/{total_books_to_process}: Copied to Obsidian")

            log.append("")

        progress(1.0, desc="🎉 All done!")
        log.append("🎉 All done!")
        return "\n".join(log), files

    except Exception as e:
        log.append(f"❌ Error: {str(e)}")
        return "\n".join(log), []


def create_interface() -> gr.Blocks:
    """
    Create and configure the Gradio interface.

    Returns:
        Configured Gradio Blocks interface
    """
    with gr.Blocks(title="Fable Screenshot Parser") as app:
        gr.Markdown("# Fable to Markdown")
        gr.Markdown("Convert your Fable book lists to organized markdown files")

        with gr.Row():
            with gr.Column():
                image_input = gr.Image(
                    label="Upload Fable Screenshot",
                    type="filepath"
                )

                with gr.Accordion("Options", open=False):
                    sync_raindrop = gr.Checkbox(
                        label="Sync to Raindrop.io",
                        value=False,
                        info="Upload books as bookmarks to Raindrop.io"
                    )
                    sync_obsidian = gr.Checkbox(
                        label="Copy to Obsidian Vault",
                        value=False,
                        info="Copy markdown files to your Obsidian vault"
                    )

                process_btn = gr.Button("Process Screenshot", variant="primary")

            with gr.Column():
                status_output = gr.Textbox(
                    label="Processing Status",
                    lines=10,
                    interactive=False
                )

                files_output = gr.File(
                    label="Generated Markdown Files",
                    file_count="multiple"
                )

        gr.Markdown("---")
        gr.Markdown("### Example Obsidian Path")
        gr.Code(
            value="/Users/username/Documents/Obsidian/MyVault/Books",
            language="shell",
            label="Edit in config.json"
        )

        # Connect the processing function
        process_btn.click(
            fn=process_pipeline,
            inputs=[image_input, sync_raindrop, sync_obsidian],
            outputs=[status_output, files_output]
        )

    return app


def main():
    """
    Main entry point for the application.

    Launches the Gradio interface on the local server.
    """
    app = create_interface()
    app.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7860
    )


if __name__ == "__main__":
    main()

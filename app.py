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
            yield "\n".join(log), []
            return

        log.append("")  # Blank line for readability

        # Phase 2: Enrich + Generate files sequentially (20% → 100%)
        progress(0.2, desc=f"📚 Processing {len(books)} books...")
        log.append(f"📚 Processing {len(books)} books (enrich + generate)...\n")

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
            yield "\n".join(log), []
            return

        # Process each book: enrich + generate file immediately
        total_books = len(valid_books)

        for book_num, (idx, book) in enumerate(valid_books, 1):
            # Calculate progress for this book: 20% + (80% × book_num/total)
            base_progress = 0.2 + (0.8 * (book_num - 1) / total_books)
            book_progress_range = 0.8 / total_books

            try:
                log.append(f"📖 {book_num}/{total_books}: {book.get('title', 'Unknown')}")

                # Check if file already exists before making API calls
                existing_data, existing_path = _check_existing_file(book)

                if existing_data:
                    # Use existing metadata from file
                    enriched = existing_data
                    log.append(f"  ⏭️  Using existing file (skipped API)")
                    # Still add to files list so user can download it
                    if existing_path:
                        files.append(existing_path)
                        # Yield update to show existing file in UI
                        yield "\n".join(log), files.copy()
                else:
                    # Define callback to capture search progress messages
                    def search_progress(msg: str):
                        log.append(f"    {msg}")

                    # Enrich metadata
                    progress(base_progress + book_progress_range * 0.3, desc=f"🔍 Enriching {book_num}/{total_books}")
                    enriched = metadata_enricher.enrich_book_metadata(book, progress_callback=search_progress)
                    log.append(f"  ✓ Enriched metadata")

                    # Generate markdown immediately after enrichment
                    progress(base_progress + book_progress_range * 0.6, desc=f"📝 Creating file {book_num}/{total_books}")
                    filepath = markdown_generator.generate_markdown_file(enriched)
                    files.append(filepath)
                    log.append(f"  ✓ Created: {os.path.basename(filepath)}")

                    # Yield update to show file immediately in UI
                    yield "\n".join(log), files.copy()

                # Optional syncs
                if sync_raindrop and config_handler.get_config_value("raindrop.enabled"):
                    rd_id = raindrop_sync.sync_to_raindrop(enriched, filepath)
                    log.append(f"  ☁️  Synced to Raindrop (ID: {rd_id})")
                    progress(base_progress + book_progress_range * 0.8, desc=f"☁️ Syncing {book_num}/{total_books}")

                if sync_obsidian and config_handler.get_config_value("obsidian.enabled"):
                    obsidian_sync.sync_to_obsidian(filepath)
                    log.append(f"  📝 Copied to Obsidian vault")
                    progress(base_progress + book_progress_range * 0.9, desc=f"📂 Copying {book_num}/{total_books}")

            except Exception as e:
                log.append(f"  ⚠️  Error: {str(e)}")

            log.append("")  # Blank line between books

            # Update progress after this book is complete
            progress(base_progress + book_progress_range, desc=f"📚 Processing {book_num}/{total_books} books")

        progress(1.0, desc="🎉 All done!")
        log.append("🎉 All done!")
        yield "\n".join(log), files

    except Exception as e:
        log.append(f"❌ Error: {str(e)}")
        yield "\n".join(log), []


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
        # show_progress="minimal" keeps progress visible but doesn't overlay output components
        process_btn.click(
            fn=process_pipeline,
            inputs=[image_input, sync_raindrop, sync_obsidian],
            outputs=[status_output, files_output],
            show_progress="minimal"
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

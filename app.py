"""
Gradio web interface for Fable Screenshot Parser.

This is the main entry point for the application, providing a web-based
interface for uploading screenshots and processing book lists.
"""

import gradio as gr
from typing import Tuple, List
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import vision_parser, metadata_enricher
from core import markdown_generator, raindrop_sync, obsidian_sync
from utils import config_handler


def process_pipeline(
    image_path: str,
    sync_raindrop: bool,
    sync_obsidian: bool
) -> Tuple[str, List[str]]:
    """
    Main processing pipeline for converting screenshots to markdown files.

    This function orchestrates the complete workflow:
    1. Analyze screenshot using vision parser
    2. Enrich each book with Open Library metadata
    3. Generate markdown files
    4. Optionally sync to Raindrop.io
    5. Optionally copy to Obsidian vault

    Args:
        image_path: Path to uploaded screenshot image
        sync_raindrop: Whether to sync books to Raindrop.io
        sync_obsidian: Whether to copy files to Obsidian vault

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
        log.append("📸 Analyzing screenshot...")

        # Phase 1: Vision Analysis
        books = vision_parser.parse_screenshot(image_path)
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

        # Phase 2: Parallel metadata enrichment
        log.append(f"🔍 Enriching metadata for {len(books)} books in parallel...")

        # Filter out books without required fields
        valid_books = []
        for i, book in enumerate(books, 1):
            if 'title' not in book:
                log.append(f"⚠️  Skipping book {i}: missing 'title' field")
            else:
                valid_books.append((i, book))

        if not valid_books:
            log.append("❌ No valid books to process")
            return "\n".join(log), []

        # Enrich all books in parallel using ThreadPoolExecutor
        enriched_books = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all enrichment tasks
            future_to_book = {
                executor.submit(metadata_enricher.enrich_book_metadata, book): (idx, book)
                for idx, book in valid_books
            }

            # Collect results as they complete
            for future in as_completed(future_to_book):
                idx, original_book = future_to_book[future]
                try:
                    enriched = future.result()
                    enriched_books.append((idx, enriched))
                    log.append(f"  ✓ Enriched: {enriched.get('title', 'Unknown')}")
                except Exception as e:
                    log.append(f"  ⚠️  Failed to enrich book {idx}: {str(e)}")
                    # Use original book data if enrichment fails
                    enriched_books.append((idx, original_book))

        # Sort by original index to maintain order
        enriched_books.sort(key=lambda x: x[0])
        log.append(f"✅ Metadata enrichment complete\n")

        # Phase 3-4: Generate markdown files and sync (sequential)
        for idx, enriched in enriched_books:
            log.append(f"📖 Processing {idx}/{len(books)}: {enriched.get('title', 'Unknown')}")

            # Generate markdown
            filepath = markdown_generator.generate_markdown_file(enriched)
            files.append(filepath)
            log.append(f"  ✓ Created {os.path.basename(filepath)}")

            # Optional syncs
            if sync_raindrop and config_handler.get_config_value("raindrop.enabled"):
                rd_id = raindrop_sync.sync_to_raindrop(enriched, filepath)
                log.append(f"  ☁️  Synced to Raindrop (ID: {rd_id})")

            if sync_obsidian and config_handler.get_config_value("obsidian.enabled"):
                obsidian_sync.sync_to_obsidian(filepath)
                log.append(f"  📝 Copied to Obsidian vault")

            log.append("")

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

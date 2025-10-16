"""
Gradio web interface for Fable Screenshot Parser.

This is the main entry point for the application, providing a web-based
interface for uploading screenshots and processing book lists.
"""

import gradio as gr
from typing import Tuple, List
import os


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
        log.append("Analyzing screenshot...")

        # from core import vision_parser, metadata_enricher
        # from core import markdown_generator, raindrop_sync, obsidian_sync
        # from utils import config_handler

        # Phase 1: Vision Analysis
        # books = vision_parser.parse_screenshot(image_path)
        # log.append(f"Found {len(books)} books\n")

        # Phase 2-4: Process each book
        # for i, book in enumerate(books, 1):
        #     log.append(f"Processing {i}/{len(books)}: {book['title']}")
        #
        #     # Enrich metadata
        #     enriched = metadata_enricher.enrich_book_metadata(book)
        #
        #     # Generate markdown
        #     filepath = markdown_generator.generate_markdown_file(enriched)
        #     files.append(filepath)
        #     log.append(f"  Created {os.path.basename(filepath)}")
        #
        #     # Optional syncs
        #     if sync_raindrop and config_handler.is_raindrop_enabled():
        #         rd_id = raindrop_sync.sync_to_raindrop(enriched, filepath)
        #         log.append(f"  Synced to Raindrop (ID: {rd_id})")
        #
        #     if sync_obsidian and config_handler.is_obsidian_enabled():
        #         obsidian_sync.sync_to_obsidian(filepath)
        #         log.append(f"  Copied to Obsidian vault")
        #
        #     log.append("")

        log.append("All done!")
        return "\n".join(log), files

    except Exception as e:
        log.append(f"Error: {str(e)}")
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
            language="bash",
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

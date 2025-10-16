# Fable Screenshot Parser - Project Specification

**Version:** 1.0.0  
**Last Updated:** October 16, 2025

---

## 📖 Project Overview

Convert Fable book list screenshots into structured markdown files with YAML frontmatter, automatically enriched with metadata from Open Library API. Export to local filesystem (Obsidian) and/or Raindrop.io via API.

---

## 🎯 Core Objective

**Input:** Stitched screenshot of Fable book list  
**Process:** Vision-based parsing → Metadata enrichment → Markdown generation  
**Output:** Individual markdown files + optional API syncs

---

## 🏗️ System Architecture

```
┌─────────────────┐
│  Gradio UI      │
│  (Web Interface)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ LLM_Inference.py│────▶│ Claude API       │
│ (Abstraction)   │     │ (Vision Analysis)│
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Book Parser     │────▶│ Open Library API │
│ (Metadata)      │     │ (ISBN, Covers)   │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Markdown        │
│ Generator       │
└────────┬────────┘
         │
         ├────────────────┬─────────────────┐
         ▼                ▼                 ▼
  ┌──────────┐    ┌─────────────┐   ┌──────────────┐
  │ /outputs/│    │ Obsidian    │   │ Raindrop.io  │
  │ (Local)  │    │ (Filesystem)│   │ (API)        │
  └──────────┘    └─────────────┘   └──────────────┘
```

---

## 📂 Project Structure

```
fable-to-markdown/
├── README.md
├── requirements.txt
├── .gitignore
├── config.json                 # User-editable settings
├── secrets.json               # API keys (NEVER commit)
├── app.py                     # Gradio interface
│
├── core/
│   ├── __init__.py
│   ├── llm_inference.py       # LLM abstraction layer
│   ├── vision_parser.py       # Screenshot analysis
│   ├── metadata_enricher.py   # Open Library API calls
│   ├── markdown_generator.py  # File creation
│   ├── raindrop_sync.py       # Raindrop.io API
│   └── obsidian_sync.py       # Filesystem operations
│
├── utils/
│   ├── __init__.py
│   ├── config_handler.py      # Load config.json
│   ├── secrets_handler.py     # Load secrets.json (validate)
│   └── validators.py          # Input validation
│
├── input/
│   └── .gitkeep
│
├── output/
│   └── .gitkeep
│
└── tests/
    └── test_pipeline.py
```

---

## 🔧 Configuration Files

### `secrets.json` (Template)
```json
{
  "anthropic_api_key": "sk-ant-...",
  "raindrop_api_token": "your-test-token-here",
  "open_library_enabled": true
}
```

### `config.json` (User Settings)
```json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 4000,
    "temperature": 0.3
  },
  "output": {
    "directory": "./output",
    "filename_format": "{author_last}_{title_slug}",
    "date_format": "%Y-%m-%d"
  },
  "obsidian": {
    "enabled": false,
    "vault_path": "/Users/username/Documents/Obsidian/MyVault/Books",
    "create_index": true
  },
  "raindrop": {
    "enabled": false,
    "collection_id": null,
    "default_tags": ["books", "fable-import"]
  },
  "metadata": {
    "default_status": "want-to-read",
    "include_cover_image": true,
    "fetch_timeout": 10
  },
  "frontmatter_fields": [
    "title",
    "author",
    "isbn",
    "cover_url",
    "source",
    "date_added",
    "status",
    "reading_status"
  ]
}
```

---

## 📋 Markdown Output Format

### Example Output: `sanderson_way-of-kings.md`

```markdown
---
title: "The Way of Kings"
author: "Brandon Sanderson"
isbn: "9780765326355"
isbn_10: "0765326353"
cover_url: "https://covers.openlibrary.org/b/isbn/9780765326355-L.jpg"
open_library_id: "OL27214493M"
source: "fable"
date_added: "2025-10-16"
status: "want-to-read"
reading_status: "unread"
publisher: "Tor Books"
publish_year: 2010
pages: 1007
---

# The Way of Kings

**Author:** Brandon Sanderson  
**ISBN-13:** 9780765326355  
**ISBN-10:** 0765326353  
**Publisher:** Tor Books (2010)  
**Pages:** 1,007

![Book Cover](https://covers.openlibrary.org/b/isbn/9780765326355-L.jpg)

## Reading Status
📚 Want to Read

## Links
- [Open Library](https://openlibrary.org/isbn/9780765326355)
- [View on Raindrop](https://app.raindrop.io/my/0/item/[ID])

---

*Imported from Fable on October 16, 2025*
```

---

## 🔌 API Integrations

### Open Library API

Open Library provides multiple APIs for accessing book data, with the Books API supporting lookups by ISBN, LCCN, OCLC, and OLID.

**Why Open Library?**
- ✅ **Free** and open-source
- ✅ **No API key required** for basic usage
- ✅ **Comprehensive** metadata (3M+ books)
- ✅ Book covers accessible via simple URL patterns with ISBN
- ✅ Reliable uptime (Internet Archive backed)

**Key Endpoints:**
```python
# Search by ISBN
GET https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data

# Get cover image
GET https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg

# Search by title/author (fallback)
GET https://openlibrary.org/search.json?title={title}&author={author}
```

**Response Fields Used:**
- `title`, `subtitle`
- `authors[].name`
- `publishers[].name`
- `publish_date`
- `number_of_pages`
- `identifiers.isbn_13[]`, `identifiers.isbn_10[]`
- `cover.large`, `cover.medium`, `cover.small`

---

### Raindrop.io API

Raindrop.io provides a public API that accepts arguments as URL-encoded values or JSON-encoded objects with OAuth authentication.

**Authentication:**
Create a test token from the Raindrop integration app settings, which provides access to your own account's bookmarks.

**Key Endpoint:**
```python
POST https://api.raindrop.io/rest/v1/raindrop
Headers:
  Content-Type: application/json
  Authorization: Bearer {token}

Body:
{
  "link": "https://openlibrary.org/isbn/{isbn}",
  "title": "{book_title}",
  "excerpt": "Author: {author} | ISBN: {isbn}",
  "collection": {
    "$id": {collection_id}
  },
  "tags": ["books", "fable-import"],
  "cover": "{cover_image_url}"
}
```

**Response:**
Returns raindrop ID for linking in markdown.

---

## 🧠 LLM Inference Abstraction

### `core/llm_inference.py`

**Purpose:** Abstract LLM provider calls to allow easy switching between providers.

**Interface:**
```python
class LLMInference:
    """Abstraction layer for LLM API calls."""
    
    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        self.api_key = secrets_handler.get_key(f"{provider}_api_key")
        self.client = self._initialize_client()
    
    def analyze_screenshot(
        self, 
        image_path: str, 
        prompt: str,
        model: str = None,
        max_tokens: int = 4000
    ) -> dict:
        """
        Analyze screenshot using vision model.
        
        Returns:
            {
                "books": [
                    {
                        "title": "Book Title",
                        "author": "Author Name",
                        "reading_status": "want-to-read"
                    },
                    ...
                ],
                "confidence": 0.95,
                "raw_response": "..."
            }
        """
        pass
    
    def _initialize_client(self):
        """Initialize provider-specific client."""
        if self.provider == "anthropic":
            return anthropic.Anthropic(api_key=self.api_key)
        # Future: Add OpenAI, Google, etc.
        raise ValueError(f"Unsupported provider: {self.provider}")
```

**Vision Prompt Template:**
```
You are analyzing a screenshot from the Fable reading app showing a list of books.

TASK:
Extract all visible books with their:
1. Title (exact as shown)
2. Author name (exact as shown)
3. Reading status (infer from visual indicators like shelves/lists)
   - Options: "read", "currently-reading", "want-to-read", "unknown"

INSTRUCTIONS:
- Be precise with titles and authors
- If a book is partially visible, include it if title is readable
- Return structured JSON only
- If you see shelf/list names like "Want to Read", use that for status

OUTPUT FORMAT:
{
  "books": [
    {
      "title": "The Way of Kings",
      "author": "Brandon Sanderson",
      "reading_status": "want-to-read"
    }
  ]
}
```

---

## 🔄 Processing Pipeline

### Phase 1: Screenshot Upload
```python
# app.py - Gradio interface
def upload_screenshot(image):
    """Handle screenshot upload."""
    # Validate image
    # Save to input/ directory
    # Return preview
```

### Phase 2: Vision Analysis
```python
# core/vision_parser.py
def parse_screenshot(image_path: str) -> list[dict]:
    """
    Extract book list from screenshot.
    
    Returns:
        [
            {
                "title": "Book Title",
                "author": "Author Name", 
                "reading_status": "want-to-read"
            },
            ...
        ]
    """
    llm = LLMInference()
    result = llm.analyze_screenshot(image_path, VISION_PROMPT)
    return result["books"]
```

### Phase 3: Metadata Enrichment
```python
# core/metadata_enricher.py
def enrich_book_metadata(book: dict) -> dict:
    """
    Query Open Library for additional metadata.
    
    Priority:
    1. Search by title + author
    2. Get first matching edition
    3. Fetch ISBN, cover, pages, etc.
    
    Returns enriched book dict with:
        - isbn, isbn_10
        - cover_url
        - publisher, publish_year
        - pages
        - open_library_id
    """
    pass
```

### Phase 4: Markdown Generation
```python
# core/markdown_generator.py
def generate_markdown_file(book: dict) -> str:
    """
    Create markdown file with YAML frontmatter.
    
    Returns: filepath of created file
    """
    # Build frontmatter
    # Generate markdown body
    # Save to output/
    # Return filepath
```

### Phase 5: Optional Syncs
```python
# core/raindrop_sync.py
def sync_to_raindrop(book: dict, markdown_path: str) -> str:
    """Sync book to Raindrop.io. Returns raindrop ID."""
    pass

# core/obsidian_sync.py
def sync_to_obsidian(markdown_path: str) -> bool:
    """Copy markdown file to Obsidian vault."""
    pass
```

---

## 🖥️ Gradio Interface (MVP)

### Layout

```python
import gradio as gr

with gr.Blocks(title="Fable Screenshot Parser") as app:
    gr.Markdown("# 📚 Fable to Markdown")
    gr.Markdown("Convert your Fable book lists to organized markdown files")
    
    with gr.Row():
        with gr.Column():
            image_input = gr.Image(
                label="Upload Fable Screenshot",
                type="filepath"
            )
            
            with gr.Accordion("⚙️ Options", open=False):
                sync_raindrop = gr.Checkbox(
                    label="Sync to Raindrop.io",
                    value=False
                )
                sync_obsidian = gr.Checkbox(
                    label="Copy to Obsidian Vault",
                    value=False
                )
                
            process_btn = gr.Button("🚀 Process Screenshot", variant="primary")
            
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
    gr.Markdown("### 📖 Example Obsidian Path")
    gr.Code(
        value="/Users/username/Documents/Obsidian/MyVault/Books",
        language="bash",
        label="Edit in config.json"
    )
    
    process_btn.click(
        fn=process_pipeline,
        inputs=[image_input, sync_raindrop, sync_obsidian],
        outputs=[status_output, files_output]
    )

if __name__ == "__main__":
    app.launch(share=False)
```

### Processing Function
```python
def process_pipeline(
    image_path: str,
    sync_raindrop: bool,
    sync_obsidian: bool
) -> tuple[str, list[str]]:
    """
    Main processing pipeline.
    
    Returns:
        (status_log, list_of_file_paths)
    """
    log = []
    files = []
    
    try:
        log.append("📸 Analyzing screenshot...")
        books = vision_parser.parse_screenshot(image_path)
        log.append(f"✅ Found {len(books)} books\n")
        
        for i, book in enumerate(books, 1):
            log.append(f"📖 Processing {i}/{len(books)}: {book['title']}")
            
            # Enrich metadata
            enriched = metadata_enricher.enrich_book_metadata(book)
            
            # Generate markdown
            filepath = markdown_generator.generate_markdown_file(enriched)
            files.append(filepath)
            log.append(f"  ✓ Created {os.path.basename(filepath)}")
            
            # Optional syncs
            if sync_raindrop and config.raindrop.enabled:
                rd_id = raindrop_sync.sync_to_raindrop(enriched, filepath)
                log.append(f"  ☁️  Synced to Raindrop (ID: {rd_id})")
            
            if sync_obsidian and config.obsidian.enabled:
                obsidian_sync.sync_to_obsidian(filepath)
                log.append(f"  📝 Copied to Obsidian vault")
            
            log.append("")
        
        log.append("🎉 All done!")
        return "\n".join(log), files
        
    except Exception as e:
        log.append(f"❌ Error: {str(e)}")
        return "\n".join(log), []
```

---

## 🔐 Security & Secrets Management

### `utils/secrets_handler.py`

```python
import json
import os
from pathlib import Path

class SecretsHandler:
    """Secure secrets management."""
    
    def __init__(self, secrets_path: str = "secrets.json"):
        self.secrets_path = Path(secrets_path)
        self._validate_secrets_file()
        self._secrets = self._load_secrets()
    
    def _validate_secrets_file(self):
        """Ensure secrets.json exists and is not committed."""
        if not self.secrets_path.exists():
            raise FileNotFoundError(
                f"{self.secrets_path} not found. "
                "Create it from secrets.json.template"
            )
        
        # Check .gitignore
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            if "secrets.json" not in content:
                print("⚠️  WARNING: secrets.json not in .gitignore!")
    
    def _load_secrets(self) -> dict:
        """Load secrets from JSON file."""
        with open(self.secrets_path) as f:
            return json.load(f)
    
    def get_key(self, key_name: str) -> str:
        """Retrieve API key by name."""
        value = self._secrets.get(key_name)
        if not value:
            raise ValueError(f"Secret '{key_name}' not found in secrets.json")
        return value
    
    def has_key(self, key_name: str) -> bool:
        """Check if key exists."""
        return key_name in self._secrets and bool(self._secrets[key_name])
```

### `.gitignore`
```
# Secrets
secrets.json
*.env

# API Keys
anthropic_key.txt
raindrop_token.txt

# Input/Output
input/*.png
input/*.jpg
output/*.md

# Python
__pycache__/
*.pyc
.pytest_cache/
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
```

---

## 📦 Dependencies

### `requirements.txt`
```
# Core
gradio==5.0.0
anthropic==0.39.0
requests==2.32.3
Pillow==10.4.0

# Utilities
python-slugify==8.0.4
python-dotenv==1.0.1
pyyaml==6.0.2

# Open Library (no separate package needed - REST API)

# Raindrop (optional Python wrapper)
raindrop-io-py==0.10.0

# Development
pytest==8.3.3
black==24.10.0
```

---

## 🎯 MVP Feature Checklist

### ✅ Core Features (v1.0)
- [x] Gradio web interface
- [x] Screenshot upload
- [x] LLM-based vision parsing (via Claude)
- [x] Open Library metadata enrichment
- [x] Markdown file generation with frontmatter
- [x] Reading status detection (read/currently-reading/want-to-read)
- [x] Local output directory
- [x] Config management (config.json)
- [x] Secrets management (secrets.json)

### ✅ Optional Syncs (v1.0)
- [x] Raindrop.io API integration (checkbox in UI)
- [x] Obsidian filesystem sync (checkbox in UI)

### 🚫 Explicitly Out of Scope (v1.0)
- ❌ Tag extraction/generation (future)
- ❌ Batch processing multiple screenshots (future)
- ❌ Goodreads integration (API restricted)
- ❌ Reading progress tracking (future)
- ❌ Book recommendations (future)
- ❌ Mobile app (future)

---

## 🔮 Future Enhancements (v2.0+)

### Phase 2
- Batch processing (multiple screenshots)
- Custom tag rules
- Reading notes field
- Book reviews import
- Export to other formats (CSV, JSON, Notion)

### Phase 3
- Direct Fable API integration (if they add export)
- Auto-tagging using LLM
- Duplicate detection
- Update existing markdown files
- Chrome extension for one-click capture

---

## 🚀 Getting Started

### Installation
```bash
# Clone repo
git clone https://github.com/AutumnsGrove/fable-to-markdown
cd fable-to-markdown

# Install dependencies
pip install -r requirements.txt

# Setup secrets
cp secrets.json.template secrets.json
# Edit secrets.json with your API keys

# Configure settings
# Edit config.json with your preferences

# Run
python app.py
```

### First Run
1. Open Fable app on iOS
2. Take screenshots of your book lists
3. Stitch screenshots using Picsew or Tailor
4. Upload stitched image to Gradio interface
5. Check options (Raindrop/Obsidian)
6. Click "Process Screenshot"
7. Download generated markdown files
8. Review output/ directory

---

## 📊 Success Metrics

**Quality:**
- 95%+ accuracy on book title extraction
- 90%+ accuracy on author extraction
- 85%+ successful Open Library matches

**Performance:**
- Parse 20 books in <30 seconds
- Metadata enrichment <2 seconds per book
- Total pipeline <60 seconds for typical screenshot

**Usability:**
- Zero-config default setup
- One-click processing
- Clear error messages
- Progress indicators

---

## ⚠️ Known Limitations

1. **OCR Dependent:** Quality depends on screenshot clarity
2. **API Rate Limits:** Open Library has soft rate limits
3. **Cover Images:** Not all books have covers in Open Library
4. **Reading Status:** Inferred from visual cues (not 100% accurate)
5. **Duplicate Detection:** Not implemented in v1.0

---

## 🤝 Contributing

See CONTRIBUTING.md for guidelines.

---

## 📄 License

MIT License - See LICENSE file for details

---

## 📞 Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Email: support@example.com

---

**End of Specification**

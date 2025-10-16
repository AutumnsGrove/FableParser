# Fable Screenshot Parser

Convert Fable book list screenshots into structured markdown files with YAML frontmatter, automatically enriched with metadata from Open Library API.

## Features

- **Vision-based parsing**: Extract book titles and authors from screenshots using Claude AI
- **Metadata enrichment**: Automatically fetch ISBN, cover images, publisher info, and more from Open Library
- **Markdown generation**: Create beautiful markdown files with YAML frontmatter
- **Reading status detection**: Automatically detect read/currently-reading/want-to-read status
- **Multiple export options**:
  - Local filesystem output
  - Obsidian vault sync
  - Raindrop.io bookmark sync
- **Web interface**: Easy-to-use Gradio UI for uploading and processing screenshots

## Quick Start

### Prerequisites

- Python 3.8+
- UV package manager (recommended) or pip
- Anthropic API key (for Claude vision analysis)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AutumnsGrove/fable-to-markdown
   cd fable-to-markdown
   ```

2. **Install dependencies**
   ```bash
   # Using UV (recommended)
   uv pip install -r requirements.txt

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Setup secrets**
   ```bash
   cp secrets.json.template secrets.json
   ```

   Edit `secrets.json` and add your API keys:
   ```json
   {
     "anthropic_api_key": "sk-ant-your-key-here",
     "raindrop_api_token": "your-raindrop-token (optional)",
     "open_library_enabled": true
   }
   ```

4. **Configure settings** (optional)

   Edit `config.json` to customize:
   - Output directory path
   - Filename format
   - Obsidian vault path
   - Raindrop.io settings
   - Default metadata fields

### Usage

1. **Run the application**
   ```bash
   # Using UV
   uv run python app.py

   # Or using python directly
   python app.py
   ```

2. **Open your browser**

   Navigate to the URL shown in the terminal (typically `http://127.0.0.1:7860`)

3. **Process screenshots**
   - Upload a Fable screenshot (stitched using Picsew or Tailor recommended)
   - Select sync options (Raindrop/Obsidian) if desired
   - Click "Process Screenshot"
   - Download generated markdown files from the output directory

## How It Works

```
Screenshot → Claude Vision API → Book List Extraction
                                        ↓
                              Open Library API Enrichment
                                        ↓
                              Markdown File Generation
                                        ↓
                    ┌───────────────────┼───────────────────┐
                    ↓                   ↓                   ↓
              Local Output        Obsidian Vault      Raindrop.io
```

## Project Structure

```
fable-to-markdown/
├── app.py                      # Gradio web interface
├── config.json                 # User configuration
├── secrets.json.template       # API keys template
├── requirements.txt            # Python dependencies
│
├── core/                       # Core functionality
│   ├── llm_inference.py        # LLM abstraction layer
│   ├── vision_parser.py        # Screenshot analysis
│   ├── metadata_enricher.py    # Open Library API calls
│   ├── markdown_generator.py   # Markdown file creation
│   ├── raindrop_sync.py        # Raindrop.io integration
│   └── obsidian_sync.py        # Obsidian filesystem sync
│
├── utils/                      # Utility functions
│   ├── config_handler.py       # Configuration management
│   ├── secrets_handler.py      # Secure secrets handling
│   └── validators.py           # Input validation
│
├── input/                      # Screenshot uploads (gitignored)
├── output/                     # Generated markdown files
└── tests/                      # Test suite
    └── test_pipeline.py
```

## Example Output

When you process a screenshot, the tool generates markdown files like this:

**sanderson_way-of-kings.md**
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

---

*Imported from Fable on October 16, 2025*
```

## Configuration

### API Keys (`secrets.json`)

```json
{
  "anthropic_api_key": "sk-ant-...",       // Required for vision analysis
  "raindrop_api_token": "...",             // Optional: for Raindrop.io sync
  "open_library_enabled": true              // Use Open Library API
}
```

**Getting API Keys:**
- **Anthropic**: Sign up at [console.anthropic.com](https://console.anthropic.com)
- **Raindrop.io**: Create test token at [app.raindrop.io/settings/integrations](https://app.raindrop.io/settings/integrations)

### User Settings (`config.json`)

Key settings you can customize:

- **LLM Provider**: Choose between Anthropic Claude models
- **Output Directory**: Where to save generated markdown files
- **Filename Format**: Template for generated filenames
- **Obsidian Integration**: Path to your Obsidian vault
- **Raindrop Settings**: Collection ID and default tags
- **Metadata Fields**: Which fields to include in frontmatter

## API Integrations

### Open Library

Free, no API key required. Provides:
- Book metadata (title, author, publisher)
- ISBN information
- Cover images
- Publication details

**Rate Limits:** Soft limits apply; the tool respects API guidelines.

### Raindrop.io (Optional)

Sync books as bookmarks with:
- Cover images
- Tags and collections
- Links to Open Library
- Custom descriptions

### Obsidian (Optional)

Automatically copy markdown files to your Obsidian vault for:
- Book tracking and notes
- Integration with your PKM system
- Link to other notes

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=core --cov=utils

# Run specific test file
uv run pytest tests/test_pipeline.py
```

### Code Formatting

This project uses Black for code formatting:

```bash
# Format all files
black .

# Check formatting without changes
black --check .
```

### Project Documentation

See `FABLEPARSER_PROJECT_SPEC.md` for detailed technical specifications.

## Limitations

- **Screenshot Quality**: Accuracy depends on image clarity
- **API Rate Limits**: Open Library has soft rate limits
- **Cover Images**: Not all books have covers available
- **Reading Status**: Inferred from visual cues (may not be 100% accurate)
- **Duplicate Detection**: Not implemented in v1.0

## Roadmap

### v1.0 (Current)
- ✅ Core screenshot parsing
- ✅ Open Library integration
- ✅ Markdown generation
- ✅ Raindrop.io sync
- ✅ Obsidian sync

### v2.0 (Planned)
- [ ] Batch processing (multiple screenshots)
- [ ] Custom tag rules
- [ ] Reading notes field
- [ ] Export to CSV/JSON/Notion
- [ ] Duplicate detection

### v3.0 (Future)
- [ ] Direct Fable API integration
- [ ] Auto-tagging using LLM
- [ ] Update existing markdown files
- [ ] Chrome extension for one-click capture

## Troubleshooting

### "secrets.json not found"
Create the file from the template: `cp secrets.json.template secrets.json`

### "API key not found"
Edit `secrets.json` and add your Anthropic API key

### "Module not found" errors
Install dependencies: `uv pip install -r requirements.txt`

### Poor parsing accuracy
- Ensure screenshots are clear and high resolution
- Use stitched screenshots from Picsew or Tailor
- Avoid screenshots with UI overlays or partial text

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (following commit style guide)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See `GIT_COMMIT_STYLE_GUIDE.md` for commit message conventions.

## License

MIT License - See LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/AutumnsGrove/fable-to-markdown/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AutumnsGrove/fable-to-markdown/discussions)

## Acknowledgments

- [Anthropic Claude](https://www.anthropic.com/) for vision AI capabilities
- [Open Library](https://openlibrary.org/) for free book metadata
- [Raindrop.io](https://raindrop.io/) for bookmark management API
- [Gradio](https://gradio.app/) for the easy-to-use web interface

---

**Made with ❤️ for book lovers who want to organize their reading lists**

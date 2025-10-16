"""
Basic test structure for the Fable Screenshot Parser pipeline.

This module contains tests for the core processing pipeline,
including vision parsing, metadata enrichment, and file generation.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
from PIL import Image


# Fixtures
@pytest.fixture
def sample_book_data() -> Dict[str, Any]:
    """
    Provide sample book data for testing.

    Returns:
        Dictionary containing sample book metadata
    """
    return {
        "title": "The Way of Kings",
        "author": "Brandon Sanderson",
        "reading_status": "want-to-read"
    }


@pytest.fixture
def enriched_book_data() -> Dict[str, Any]:
    """
    Provide enriched book data for testing.

    Returns:
        Dictionary containing sample enriched book metadata
    """
    return {
        "title": "The Way of Kings",
        "author": "Brandon Sanderson",
        "reading_status": "want-to-read",
        "isbn": "9780765326355",
        "isbn_10": "0765326353",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780765326355-L.jpg",
        "publisher": "Tor Books",
        "publish_year": 2010,
        "pages": 1007,
        "open_library_id": "OL27214493M"
    }


@pytest.fixture
def sample_screenshot_path(tmp_path) -> str:
    """
    Create a temporary sample screenshot file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary screenshot file
    """
    # Create a small test image
    img = Image.new('RGB', (100, 100), color='white')
    image_path = tmp_path / "test_screenshot.png"
    img.save(str(image_path))
    return str(image_path)


@pytest.fixture
def mock_config(tmp_path):
    """
    Provide mock configuration for testing.

    Returns:
        Dictionary containing test configuration
    """
    return {
        "llm": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000
        },
        "output": {
            "directory": str(tmp_path / "output"),
            "filename_format": "{author_last}_{title_slug}",
            "date_format": "%Y-%m-%d"
        },
        "obsidian": {
            "enabled": False,
            "vault_path": str(tmp_path / "obsidian")
        },
        "raindrop": {
            "enabled": False,
            "collection_id": None,
            "default_tags": ["books", "fable-import"]
        },
        "frontmatter_fields": [
            "title", "author", "isbn", "reading_status"
        ]
    }


@pytest.fixture
def mock_secrets():
    """
    Provide mock secrets for testing.

    Returns:
        Dictionary containing test API keys
    """
    return {
        "anthropic_api_key": "sk-ant-test-key-123",
        "raindrop_api_token": "test-raindrop-token-456"
    }


@pytest.fixture
def mock_open_library_response():
    """
    Provide mock Open Library API response.

    Returns:
        Dictionary simulating Open Library API response
    """
    return {
        "docs": [
            {
                "key": "OL27214493M",
                "title": "The Way of Kings",
                "author_name": ["Brandon Sanderson"],
                "isbn": ["9780765326355", "0765326353"],
                "publisher": ["Tor Books"],
                "first_publish_year": 2010,
                "publish_year": [2010],
                "number_of_pages_median": 1007
            }
        ]
    }


# Vision Parser Tests
class TestVisionParser:
    """Tests for vision_parser module."""

    @patch('core.vision_parser.LLMInference')
    def test_parse_screenshot_returns_list(self, mock_llm_class, sample_screenshot_path):
        """Test that parse_screenshot returns a list of books."""
        from core.vision_parser import parse_screenshot

        # Mock LLM response
        mock_llm = Mock()
        mock_llm.analyze_screenshot.return_value = {
            "books": [
                {
                    "title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "reading_status": "want-to-read"
                }
            ],
            "confidence": 0.95
        }
        mock_llm_class.return_value = mock_llm

        # Call function
        result = parse_screenshot(sample_screenshot_path)

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "The Way of Kings"

    def test_parse_screenshot_validates_image(self):
        """Test that parse_screenshot validates image file exists."""
        from core.vision_parser import parse_screenshot

        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            parse_screenshot("/path/to/nonexistent/image.png")

    @patch('core.vision_parser.LLMInference')
    def test_parse_screenshot_extracts_required_fields(self, mock_llm_class, sample_screenshot_path):
        """Test that parse_screenshot extracts title, author, and status."""
        from core.vision_parser import parse_screenshot

        # Mock LLM response with multiple books
        mock_llm = Mock()
        mock_llm.analyze_screenshot.return_value = {
            "books": [
                {
                    "title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "reading_status": "want-to-read"
                },
                {
                    "title": "Project Hail Mary",
                    "author": "Andy Weir",
                    "reading_status": "read"
                }
            ]
        }
        mock_llm_class.return_value = mock_llm

        # Call function
        result = parse_screenshot(sample_screenshot_path)

        # Verify all books have required fields
        for book in result:
            assert "title" in book
            assert "author" in book
            assert "reading_status" in book


# Metadata Enricher Tests
class TestMetadataEnricher:
    """Tests for metadata_enricher module."""

    @patch('core.metadata_enricher.requests.get')
    def test_enrich_book_metadata_adds_isbn(self, mock_get, sample_book_data, mock_open_library_response):
        """Test that enrich_book_metadata adds ISBN information."""
        from core.metadata_enricher import enrich_book_metadata

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = mock_open_library_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call function
        result = enrich_book_metadata(sample_book_data)

        # Assertions
        assert "isbn" in result
        assert result["isbn"] in ["9780765326355", "0765326353"]

    @patch('core.metadata_enricher.requests.get')
    def test_enrich_book_metadata_adds_cover_url(self, mock_get, sample_book_data, mock_open_library_response):
        """Test that enrich_book_metadata adds cover URL."""
        from core.metadata_enricher import enrich_book_metadata

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = mock_open_library_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call function
        result = enrich_book_metadata(sample_book_data)

        # Assertions
        assert "cover_url" in result
        assert "openlibrary.org" in result["cover_url"]

    @patch('core.metadata_enricher.requests.get')
    def test_enrich_book_metadata_handles_not_found(self, mock_get):
        """Test that enrich_book_metadata handles books not in Open Library."""
        from core.metadata_enricher import enrich_book_metadata

        # Mock empty API response
        mock_response = Mock()
        mock_response.json.return_value = {"docs": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        book_data = {
            "title": "Nonexistent Book",
            "author": "Unknown Author",
            "reading_status": "want-to-read"
        }

        # Call function
        result = enrich_book_metadata(book_data)

        # Should return original data with note
        assert result["title"] == "Nonexistent Book"
        assert result["author"] == "Unknown Author"
        assert result.get("metadata_source") == "No Open Library match"

    @patch('core.metadata_enricher.requests.get')
    def test_enrich_book_metadata_preserves_original_fields(self, mock_get, sample_book_data, mock_open_library_response):
        """Test that original book fields are preserved after enrichment."""
        from core.metadata_enricher import enrich_book_metadata

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = mock_open_library_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call function
        result = enrich_book_metadata(sample_book_data)

        # Original fields should be preserved
        assert result["title"] == sample_book_data["title"]
        assert result["author"] == sample_book_data["author"]
        assert result["reading_status"] == sample_book_data["reading_status"]


# Markdown Generator Tests
class TestMarkdownGenerator:
    """Tests for markdown_generator module."""

    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    def test_generate_markdown_creates_file(self, mock_get_config, mock_get_dir, enriched_book_data, tmp_path):
        """Test that generate_markdown_file creates a file."""
        from core.markdown_generator import generate_markdown_file

        # Setup mocks
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_get_dir.return_value = str(output_dir)
        mock_get_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "output.date_format": "%Y-%m-%d",
            "frontmatter_fields": ["title", "author", "isbn"]
        }.get(key, default)

        # Call function
        filepath = generate_markdown_file(enriched_book_data)

        # Assertions
        assert os.path.exists(filepath)
        assert filepath.endswith(".md")

    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    def test_generate_markdown_includes_frontmatter(self, mock_get_config, mock_get_dir, enriched_book_data, tmp_path):
        """Test that generated markdown includes YAML frontmatter."""
        from core.markdown_generator import generate_markdown_file

        # Setup mocks
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_get_dir.return_value = str(output_dir)
        mock_get_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "output.date_format": "%Y-%m-%d",
            "frontmatter_fields": ["title", "author", "isbn"]
        }.get(key, default)

        # Call function
        filepath = generate_markdown_file(enriched_book_data)

        # Read file and check frontmatter
        with open(filepath, 'r') as f:
            content = f.read()

        assert content.startswith("---")
        assert "title:" in content
        assert "author:" in content
        assert enriched_book_data["title"] in content

    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    def test_generate_markdown_filename_format(self, mock_get_config, mock_get_dir, enriched_book_data, tmp_path):
        """Test that generated filename follows {author_last}_{title_slug}.md format."""
        from core.markdown_generator import generate_markdown_file

        # Setup mocks
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_get_dir.return_value = str(output_dir)
        mock_get_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "output.date_format": "%Y-%m-%d",
            "frontmatter_fields": ["title", "author"]
        }.get(key, default)

        # Call function
        filepath = generate_markdown_file(enriched_book_data)

        # Check filename format
        filename = os.path.basename(filepath)
        assert filename.startswith("sanderson_")
        assert "way-of-kings" in filename.lower()
        assert filename.endswith(".md")

    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    def test_generate_markdown_handles_missing_optional_fields(self, mock_get_config, mock_get_dir, sample_book_data, tmp_path):
        """Test that markdown generation works with minimal book data."""
        from core.markdown_generator import generate_markdown_file

        # Setup mocks
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_get_dir.return_value = str(output_dir)
        mock_get_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "output.date_format": "%Y-%m-%d",
            "frontmatter_fields": ["title", "author"]
        }.get(key, default)

        # Call function with minimal data
        filepath = generate_markdown_file(sample_book_data)

        # File should be created despite missing optional fields
        assert os.path.exists(filepath)

        # Read and verify content
        with open(filepath, 'r') as f:
            content = f.read()

        assert sample_book_data["title"] in content
        assert sample_book_data["author"] in content


# Raindrop Sync Tests
class TestRaindropSync:
    """Tests for raindrop_sync module."""

    @patch('core.raindrop_sync.secrets_handler.has_key')
    @patch('core.raindrop_sync.secrets_handler.get_key')
    @patch('core.raindrop_sync.config_handler.get_config_value')
    @patch('core.raindrop_sync.requests.post')
    def test_sync_to_raindrop_returns_id(self, mock_post, mock_config, mock_get_key, mock_has_key, enriched_book_data):
        """Test that sync_to_raindrop returns a raindrop ID."""
        from core.raindrop_sync import sync_to_raindrop

        # Setup mocks
        mock_has_key.return_value = True
        mock_get_key.return_value = "test-token"
        mock_config.side_effect = lambda key, default=None: {
            "raindrop.collection_id": "12345",
            "raindrop.default_tags": ["books", "test"]
        }.get(key, default)

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "item": {
                "_id": "67890"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Call function
        raindrop_id = sync_to_raindrop(enriched_book_data, "/path/to/file.md")

        # Assertions
        assert raindrop_id == "67890"
        mock_post.assert_called_once()

    @patch('core.raindrop_sync.secrets_handler.has_key')
    def test_sync_to_raindrop_requires_token(self, mock_has_key, enriched_book_data):
        """Test that sync_to_raindrop validates API token exists."""
        from core.raindrop_sync import sync_to_raindrop

        # Mock missing token
        mock_has_key.return_value = False

        # Should raise ValueError
        with pytest.raises(ValueError, match="Raindrop API token"):
            sync_to_raindrop(enriched_book_data, "/path/to/file.md")


# Obsidian Sync Tests
class TestObsidianSync:
    """Tests for obsidian_sync module."""

    @patch('core.obsidian_sync.config_handler.get_config_value')
    def test_sync_to_obsidian_copies_file(self, mock_config, tmp_path):
        """Test that sync_to_obsidian copies file to vault."""
        from core.obsidian_sync import sync_to_obsidian

        # Create test markdown file
        source_file = tmp_path / "source.md"
        source_file.write_text("# Test Book\n\nTest content")

        # Create vault directory
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Mock config
        mock_config.return_value = str(vault_path)

        # Call function
        result = sync_to_obsidian(str(source_file))

        # Assertions
        assert result is True
        dest_file = vault_path / "source.md"
        assert dest_file.exists()
        assert dest_file.read_text() == source_file.read_text()

    @patch('core.obsidian_sync.config_handler.get_config_value')
    def test_sync_to_obsidian_validates_vault_path(self, mock_config):
        """Test that sync_to_obsidian validates vault path exists."""
        from core.obsidian_sync import sync_to_obsidian

        # Mock non-existent vault path
        mock_config.return_value = "/nonexistent/vault/path"

        # Should raise OSError
        with pytest.raises(OSError):
            sync_to_obsidian("/some/markdown/file.md")


# Config Handler Tests
class TestConfigHandler:
    """Tests for config_handler module."""

    def test_load_config_returns_dict(self, tmp_path, mock_config):
        """Test that load_config returns a dictionary."""
        from utils.config_handler import load_config

        # Create temporary config file
        config_path = tmp_path / "test_config.json"
        with open(config_path, 'w') as f:
            json.dump(mock_config, f)

        # Load config
        config = load_config(str(config_path))

        # Assertions
        assert isinstance(config, dict)
        assert "llm" in config
        assert "output" in config

    def test_get_config_value_with_dot_notation(self, tmp_path, mock_config):
        """Test that get_config_value works with dot notation."""
        from utils import config_handler

        # Create temporary config file
        config_path = tmp_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(mock_config, f)

        # Load config first
        config_handler.load_config(str(config_path))

        # Test dot notation
        model = config_handler.get_config_value("llm.model")
        assert model == "claude-sonnet-4-20250514"

        # Test nested access
        output_format = config_handler.get_config_value("output.filename_format")
        assert output_format == "{author_last}_{title_slug}"

    def test_get_config_value_returns_default(self, tmp_path, mock_config):
        """Test that get_config_value returns default if key not found."""
        from utils import config_handler

        # Create temporary config file
        config_path = tmp_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(mock_config, f)

        # Load config first
        config_handler.load_config(str(config_path))

        # Test with non-existent key
        value = config_handler.get_config_value("nonexistent.key", "default_value")
        assert value == "default_value"


# Secrets Handler Tests
class TestSecretsHandler:
    """Tests for secrets_handler module."""

    def test_secrets_handler_loads_secrets(self, tmp_path, mock_secrets):
        """Test that SecretsHandler loads secrets.json."""
        from utils.secrets_handler import SecretsHandler

        # Create temporary secrets file
        secrets_path = tmp_path / "secrets.json"
        with open(secrets_path, 'w') as f:
            json.dump(mock_secrets, f)

        # Initialize handler
        handler = SecretsHandler(str(secrets_path))

        # Assertions
        assert handler._secrets is not None
        assert isinstance(handler._secrets, dict)

    def test_get_key_returns_value(self, tmp_path, mock_secrets):
        """Test that get_key returns secret value."""
        from utils.secrets_handler import SecretsHandler

        # Create temporary secrets file
        secrets_path = tmp_path / "secrets.json"
        with open(secrets_path, 'w') as f:
            json.dump(mock_secrets, f)

        # Initialize handler and get key
        handler = SecretsHandler(str(secrets_path))
        api_key = handler.get_key("anthropic_api_key")

        # Assertions
        assert api_key == "sk-ant-test-key-123"

    def test_get_key_raises_on_missing_key(self, tmp_path, mock_secrets):
        """Test that get_key raises ValueError for missing keys."""
        from utils.secrets_handler import SecretsHandler

        # Create temporary secrets file
        secrets_path = tmp_path / "secrets.json"
        with open(secrets_path, 'w') as f:
            json.dump(mock_secrets, f)

        # Initialize handler
        handler = SecretsHandler(str(secrets_path))

        # Should raise ValueError for missing key
        with pytest.raises(ValueError, match="not found"):
            handler.get_key("nonexistent_key")

    def test_has_key_checks_existence(self, tmp_path, mock_secrets):
        """Test that has_key correctly checks key existence."""
        from utils.secrets_handler import SecretsHandler

        # Create temporary secrets file
        secrets_path = tmp_path / "secrets.json"
        with open(secrets_path, 'w') as f:
            json.dump(mock_secrets, f)

        # Initialize handler
        handler = SecretsHandler(str(secrets_path))

        # Test existing key
        assert handler.has_key("anthropic_api_key") is True

        # Test non-existent key
        assert handler.has_key("nonexistent_key") is False


# Validators Tests
class TestValidators:
    """Tests for validators module."""

    def test_validate_image_file_accepts_valid_formats(self, tmp_path):
        """Test that validate_image_file accepts PNG, JPG, JPEG."""
        from utils.validators import validate_image_file

        # Create test image files
        for ext in ['.png', '.jpg', '.jpeg']:
            img_path = tmp_path / f"test{ext}"
            img_path.write_text("dummy image content")

            # Should not raise exception
            assert validate_image_file(str(img_path)) is True

    def test_validate_image_file_rejects_invalid_formats(self, tmp_path):
        """Test that validate_image_file rejects non-image files."""
        from utils.validators import validate_image_file

        # Create invalid file
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not an image")

        # Should raise ValueError
        with pytest.raises(ValueError, match="Unsupported image format"):
            validate_image_file(str(invalid_file))

    def test_validate_book_data_checks_required_fields(self):
        """Test that validate_book_data checks for title, author, status."""
        from utils.validators import validate_book_data

        # Valid book data
        valid_book = {
            "title": "Test Book",
            "author": "Test Author",
            "reading_status": "read"
        }
        assert validate_book_data(valid_book) is True

        # Missing title
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_book_data({"author": "Test", "reading_status": "read"})

        # Missing author
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_book_data({"title": "Test", "reading_status": "read"})

        # Missing reading_status
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_book_data({"title": "Test", "author": "Test"})

    def test_validate_isbn_accepts_valid_formats(self):
        """Test that validate_isbn accepts valid ISBN-10 and ISBN-13."""
        from utils.validators import validate_isbn

        # Valid ISBN-13
        assert validate_isbn("9780765326355") is True

        # Valid ISBN-10
        assert validate_isbn("0765326353") is True

        # Valid ISBN with hyphens
        assert validate_isbn("978-0-7653-2635-5") is True

    def test_validate_isbn_rejects_invalid_formats(self):
        """Test that validate_isbn rejects invalid ISBNs."""
        from utils.validators import validate_isbn

        # Invalid length
        assert validate_isbn("123") is False

        # Invalid characters
        assert validate_isbn("abcd-efgh-ijkl") is False

        # Empty string
        assert validate_isbn("") is False

        # None
        assert validate_isbn(None) is False

    def test_validate_reading_status_accepts_valid_values(self):
        """Test that validate_reading_status accepts valid statuses."""
        from utils.validators import validate_reading_status

        # Valid statuses
        assert validate_reading_status("read") is True
        assert validate_reading_status("currently-reading") is True
        assert validate_reading_status("want-to-read") is True
        assert validate_reading_status("unknown") is True

        # Invalid statuses
        assert validate_reading_status("invalid-status") is False
        assert validate_reading_status("") is False
        assert validate_reading_status(None) is False

    def test_sanitize_filename_removes_invalid_chars(self):
        """Test that sanitize_filename removes special characters."""
        from utils.validators import sanitize_filename

        # Test removal of invalid characters
        result = sanitize_filename("Book: Title/Path\\Name?")
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result
        assert "?" not in result

        # Test space replacement
        result = sanitize_filename("My Book Title")
        assert result == "My_Book_Title"

        # Test empty result handling
        result = sanitize_filename("///:::???")
        assert result == "unnamed_file"


# Integration Tests
class TestIntegration:
    """Integration tests for the full pipeline."""

    @patch('core.vision_parser.LLMInference')
    @patch('core.metadata_enricher.requests.get')
    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    def test_full_pipeline_screenshot_to_markdown(
        self, mock_get_config, mock_get_dir, mock_requests, mock_llm_class,
        sample_screenshot_path, tmp_path, mock_open_library_response
    ):
        """Test the complete pipeline from screenshot to markdown files."""
        from core import vision_parser, metadata_enricher, markdown_generator

        # Setup mocks - LLM
        mock_llm = Mock()
        mock_llm.analyze_screenshot.return_value = {
            "books": [{
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "reading_status": "want-to-read"
            }]
        }
        mock_llm_class.return_value = mock_llm

        # Setup mocks - Open Library
        mock_response = Mock()
        mock_response.json.return_value = mock_open_library_response
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response

        # Setup mocks - Output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_get_dir.return_value = str(output_dir)
        mock_get_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "output.date_format": "%Y-%m-%d",
            "frontmatter_fields": ["title", "author", "isbn"]
        }.get(key, default)

        # Run pipeline
        books = vision_parser.parse_screenshot(sample_screenshot_path)
        enriched = metadata_enricher.enrich_book_metadata(books[0])
        filepath = markdown_generator.generate_markdown_file(enriched)

        # Assertions
        assert len(books) == 1
        assert "isbn" in enriched
        assert os.path.exists(filepath)

    @patch('core.vision_parser.LLMInference')
    @patch('core.metadata_enricher.requests.get')
    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    def test_pipeline_handles_multiple_books(
        self, mock_get_config, mock_get_dir, mock_requests, mock_llm_class,
        sample_screenshot_path, tmp_path, mock_open_library_response
    ):
        """Test that pipeline can process multiple books from one screenshot."""
        from core import vision_parser, metadata_enricher, markdown_generator

        # Setup mocks - LLM with multiple books
        mock_llm = Mock()
        mock_llm.analyze_screenshot.return_value = {
            "books": [
                {
                    "title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "reading_status": "want-to-read"
                },
                {
                    "title": "Project Hail Mary",
                    "author": "Andy Weir",
                    "reading_status": "read"
                }
            ]
        }
        mock_llm_class.return_value = mock_llm

        # Setup mocks - Open Library
        mock_response = Mock()
        mock_response.json.return_value = mock_open_library_response
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response

        # Setup mocks - Output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_get_dir.return_value = str(output_dir)
        mock_get_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "frontmatter_fields": ["title", "author"]
        }.get(key, default)

        # Run pipeline for all books
        books = vision_parser.parse_screenshot(sample_screenshot_path)
        filepaths = []
        for book in books:
            enriched = metadata_enricher.enrich_book_metadata(book)
            filepath = markdown_generator.generate_markdown_file(enriched)
            filepaths.append(filepath)

        # Assertions
        assert len(books) == 2
        assert len(filepaths) == 2
        assert all(os.path.exists(fp) for fp in filepaths)

    @patch('core.vision_parser.LLMInference')
    @patch('core.metadata_enricher.requests.get')
    @patch('core.markdown_generator.get_output_directory')
    @patch('core.markdown_generator.get_config_value')
    @patch('core.raindrop_sync.secrets_handler.has_key')
    @patch('core.raindrop_sync.secrets_handler.get_key')
    @patch('core.raindrop_sync.config_handler.get_config_value')
    @patch('core.raindrop_sync.requests.post')
    def test_pipeline_with_sync_options(
        self, mock_rain_post, mock_rain_config, mock_rain_key,
        mock_rain_has, mock_md_config, mock_md_dir, mock_lib_get, mock_llm_class,
        sample_screenshot_path, tmp_path, mock_open_library_response
    ):
        """Test pipeline with Raindrop and Obsidian sync enabled."""
        from core import vision_parser, metadata_enricher, markdown_generator
        from core import raindrop_sync, obsidian_sync

        # Setup mocks - LLM
        mock_llm = Mock()
        mock_llm.analyze_screenshot.return_value = {
            "books": [{
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "reading_status": "want-to-read"
            }]
        }
        mock_llm_class.return_value = mock_llm

        # Setup mocks - Open Library
        mock_response = Mock()
        mock_response.json.return_value = mock_open_library_response
        mock_response.raise_for_status = Mock()
        mock_lib_get.return_value = mock_response

        # Setup mocks - Markdown generator
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mock_md_dir.return_value = str(output_dir)
        mock_md_config.side_effect = lambda key, default=None: {
            "output.filename_format": "{author_last}_{title_slug}",
            "frontmatter_fields": ["title", "author", "isbn"]
        }.get(key, default)

        # Setup mocks - Raindrop
        mock_rain_has.return_value = True
        mock_rain_key.return_value = "test-token"
        mock_rain_config.side_effect = lambda key, default=None: {
            "raindrop.collection_id": None,
            "raindrop.default_tags": ["books"]
        }.get(key, default)
        mock_rain_response = Mock()
        mock_rain_response.json.return_value = {"item": {"_id": "12345"}}
        mock_rain_response.raise_for_status = Mock()
        mock_rain_post.return_value = mock_rain_response

        # Setup mocks - Obsidian
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Run pipeline with sync options
        books = vision_parser.parse_screenshot(sample_screenshot_path)
        enriched = metadata_enricher.enrich_book_metadata(books[0])
        filepath = markdown_generator.generate_markdown_file(enriched)

        # Sync to Raindrop
        raindrop_id = raindrop_sync.sync_to_raindrop(enriched, filepath)

        # Sync to Obsidian - patch config_handler at the point of use
        with patch.object(obsidian_sync.config_handler, 'get_config_value', return_value=str(vault_path)):
            obsidian_result = obsidian_sync.sync_to_obsidian(filepath)

        # Assertions
        assert raindrop_id == "12345"
        assert obsidian_result is True
        assert (vault_path / os.path.basename(filepath)).exists()


# LLM Inference Tests
class TestLLMInference:
    """Tests for LLM inference module."""

    @patch('core.llm_inference.get_key')
    @patch('core.llm_inference.get_config_value')
    @patch('core.llm_inference.anthropic.Anthropic')
    def test_llm_inference_initialization(self, mock_anthropic, mock_config, mock_get_key):
        """Test that LLMInference initializes correctly."""
        from core.llm_inference import LLMInference

        # Setup mocks
        mock_get_key.return_value = "test-api-key"
        mock_config.return_value = "claude-sonnet-4-20250514"

        # Initialize
        llm = LLMInference()

        # Assertions
        assert llm.provider == "anthropic"
        assert llm.api_key == "test-api-key"
        mock_anthropic.assert_called_once()

    @patch('core.llm_inference.get_key')
    @patch('core.llm_inference.get_config_value')
    def test_llm_inference_unsupported_provider(self, mock_config, mock_get_key):
        """Test that unsupported provider raises ValueError."""
        from core.llm_inference import LLMInference

        # Setup mocks
        mock_get_key.return_value = "test-key"
        mock_config.return_value = "test-model"

        # Should raise ValueError for unsupported provider
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMInference(provider="unsupported_provider")

    @patch('core.llm_inference.get_key')
    @patch('core.llm_inference.get_config_value')
    @patch('core.llm_inference.anthropic.Anthropic')
    def test_analyze_screenshot_returns_structured_data(
        self, mock_anthropic, mock_config, mock_get_key, sample_screenshot_path
    ):
        """Test that analyze_screenshot returns properly structured data."""
        from core.llm_inference import LLMInference

        # Setup mocks
        mock_get_key.return_value = "test-key"
        mock_config.return_value = "claude-sonnet-4-20250514"

        # Mock Anthropic client response
        mock_client = Mock()
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = json.dumps({
            "books": [{
                "title": "Test Book",
                "author": "Test Author",
                "reading_status": "read"
            }],
            "confidence": 0.95
        })
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        # Initialize and call
        llm = LLMInference()
        result = llm.analyze_screenshot(sample_screenshot_path, "test prompt")

        # Assertions
        assert "books" in result
        assert "confidence" in result
        assert isinstance(result["books"], list)
        assert len(result["books"]) == 1

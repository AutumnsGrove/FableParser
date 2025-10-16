"""
Configuration file handler for config.json.

This module provides functions to load and access user configuration
settings such as LLM provider, output directory, and sync options.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from config.json file.

    Args:
        config_path: Path to config.json file (default: "config.json")

    Returns:
        Dictionary containing configuration settings

    Raises:
        FileNotFoundError: If config.json does not exist
        json.JSONDecodeError: If config.json is invalid JSON
    """
    pass


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value using dot notation.

    Args:
        key_path: Configuration key path (e.g., "llm.model", "output.directory")
        default: Default value if key not found

    Returns:
        Configuration value, or default if not found

    Example:
        >>> model = get_config_value("llm.model")
        >>> print(model)
        "claude-sonnet-4-20250514"

        >>> vault_path = get_config_value("obsidian.vault_path", "/default/path")
    """
    pass


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate that required configuration fields are present.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If critical configuration fields are missing
    """
    pass


def get_output_directory() -> str:
    """
    Get the configured output directory path.

    Returns:
        Absolute path to output directory

    Raises:
        ValueError: If output directory is not configured
    """
    pass


def is_obsidian_enabled() -> bool:
    """
    Check if Obsidian sync is enabled in config.

    Returns:
        True if enabled, False otherwise
    """
    pass


def is_raindrop_enabled() -> bool:
    """
    Check if Raindrop.io sync is enabled in config.

    Returns:
        True if enabled, False otherwise
    """
    pass

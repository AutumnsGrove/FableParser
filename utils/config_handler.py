"""
Configuration file handler for config.json.

This module provides functions to load and access user configuration
settings such as LLM provider, output directory, and sync options.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Global configuration cache
_CONFIG_CACHE: Optional[Dict[str, Any]] = None
_CONFIG_PATH: Optional[str] = None


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
    global _CONFIG_CACHE, _CONFIG_PATH

    # Resolve absolute path
    if not os.path.isabs(config_path):
        # Get the project root (parent of utils/)
        project_root = Path(__file__).parent.parent
        config_path = str(project_root / config_path)

    # Return cached config if same file
    if _CONFIG_CACHE is not None and _CONFIG_PATH == config_path:
        return _CONFIG_CACHE

    # Load config file
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in configuration file: {e.msg}",
            e.doc,
            e.pos
        )

    # Validate configuration
    validate_config(config)

    # Cache the configuration
    _CONFIG_CACHE = config
    _CONFIG_PATH = config_path

    return config


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
    # Load config if not cached
    config = load_config()

    # Split key path by dots
    keys = key_path.split('.')
    value = config

    # Navigate through nested dictionary
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


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
    required_fields = {
        'llm': ['provider', 'model'],
        'output': ['directory', 'filename_format'],
        'obsidian': ['enabled'],
        'raindrop': ['enabled']
    }

    missing_fields = []

    # Check top-level sections
    for section, fields in required_fields.items():
        if section not in config:
            missing_fields.append(f"Section '{section}' is missing")
            continue

        # Check required fields in each section
        for field in fields:
            if field not in config[section]:
                missing_fields.append(f"Field '{section}.{field}' is missing")

    # If any required fields are missing, raise ValueError
    if missing_fields:
        raise ValueError(
            "Configuration validation failed. Missing required fields:\n" +
            "\n".join(f"  - {field}" for field in missing_fields)
        )

    return True


def get_output_directory() -> str:
    """
    Get the configured output directory path.

    Returns:
        Absolute path to output directory

    Raises:
        ValueError: If output directory is not configured
    """
    output_dir = get_config_value("output.directory")

    if not output_dir:
        raise ValueError("Output directory is not configured in config.json")

    # Convert to absolute path if relative
    if not os.path.isabs(output_dir):
        # Get project root (parent of utils/)
        project_root = Path(__file__).parent.parent
        output_dir = str(project_root / output_dir)

    return output_dir


def is_obsidian_enabled() -> bool:
    """
    Check if Obsidian sync is enabled in config.

    Returns:
        True if enabled, False otherwise
    """
    return get_config_value("obsidian.enabled", False)


def is_raindrop_enabled() -> bool:
    """
    Check if Raindrop.io sync is enabled in config.

    Returns:
        True if enabled, False otherwise
    """
    return get_config_value("raindrop.enabled", False)

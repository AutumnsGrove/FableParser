"""
Secure secrets management for API keys and tokens.

This module provides secure handling of sensitive credentials
from secrets.json, with validation to prevent accidental commits.
"""

import json
from pathlib import Path
from typing import Dict, Any


class SecretsHandler:
    """
    Secure secrets management for API keys and tokens.

    This class loads and validates secrets from secrets.json,
    ensuring that sensitive credentials are not accidentally committed.

    Attributes:
        secrets_path: Path to secrets.json file
        _secrets: Dictionary containing loaded secrets
    """

    def __init__(self, secrets_path: str = "secrets.json"):
        """
        Initialize secrets handler.

        Args:
            secrets_path: Path to secrets.json file (default: "secrets.json")

        Raises:
            FileNotFoundError: If secrets.json does not exist
        """
        self.secrets_path = Path(secrets_path)
        self._validate_secrets_file()
        self._secrets = self._load_secrets()

    def _validate_secrets_file(self):
        """
        Ensure secrets.json exists and is not committed to git.

        Checks that:
        1. secrets.json file exists
        2. secrets.json is listed in .gitignore

        Raises:
            FileNotFoundError: If secrets.json does not exist
        """
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
                print("WARNING: secrets.json not in .gitignore!")

    def _load_secrets(self) -> Dict[str, Any]:
        """
        Load secrets from JSON file.

        Returns:
            Dictionary containing secrets

        Raises:
            json.JSONDecodeError: If secrets.json is invalid JSON
        """
        with open(self.secrets_path) as f:
            return json.load(f)

    def get_key(self, key_name: str) -> str:
        """
        Retrieve API key or token by name.

        Args:
            key_name: Name of the secret key (e.g., "anthropic_api_key")

        Returns:
            The secret value as a string

        Example:
            >>> secrets = SecretsHandler()
            >>> api_key = secrets.get_key("anthropic_api_key")
            >>> print(api_key)
            "sk-ant-..."

        Raises:
            ValueError: If the key is not found or is empty
        """
        value = self._secrets.get(key_name)
        if not value:
            raise ValueError(f"Secret '{key_name}' not found in secrets.json")
        return value

    def has_key(self, key_name: str) -> bool:
        """
        Check if a secret key exists and has a non-empty value.

        Args:
            key_name: Name of the secret key to check

        Returns:
            True if key exists and has a value, False otherwise

        Example:
            >>> secrets = SecretsHandler()
            >>> if secrets.has_key("raindrop_api_token"):
            ...     print("Raindrop token is configured")
        """
        return key_name in self._secrets and bool(self._secrets[key_name])


# Module-level convenience functions
_handler: SecretsHandler = None


def get_secrets_handler() -> SecretsHandler:
    """
    Get singleton instance of SecretsHandler.

    Returns:
        SecretsHandler instance
    """
    global _handler
    if _handler is None:
        _handler = SecretsHandler()
    return _handler


def get_key(key_name: str) -> str:
    """
    Convenience function to get a secret key.

    Args:
        key_name: Name of the secret key

    Returns:
        The secret value as a string
    """
    return get_secrets_handler().get_key(key_name)


def has_key(key_name: str) -> bool:
    """
    Convenience function to check if a key exists.

    Args:
        key_name: Name of the secret key

    Returns:
        True if key exists and has a value, False otherwise
    """
    return get_secrets_handler().has_key(key_name)

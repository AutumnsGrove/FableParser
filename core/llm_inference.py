"""
LLM Inference abstraction layer for vision analysis.

This module provides a unified interface for making LLM API calls,
currently supporting Anthropic's Claude with vision capabilities.
Future support for OpenAI, Google, and other providers can be added here.
"""

import base64
import json
from pathlib import Path
from typing import Optional, Dict, Any

import anthropic

from utils.secrets_handler import get_key
from utils.config_handler import get_config_value


class LLMInference:
    """
    Abstraction layer for LLM API calls with vision capabilities.

    Attributes:
        provider: The LLM provider (e.g., "anthropic")
        api_key: The API key for authentication
        client: The initialized provider-specific client
    """

    def __init__(self, provider: str = "anthropic"):
        """
        Initialize the LLM inference client.

        Args:
            provider: The LLM provider to use (default: "anthropic")

        Raises:
            ValueError: If API key not found or provider not supported
            FileNotFoundError: If secrets.json or config.json not found
        """
        self.provider = provider

        # Load API key from secrets_handler
        if provider == "anthropic":
            self.api_key = get_key("anthropic_api_key")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Load default model from config
        self.default_model = get_config_value("llm.model")

        # Initialize provider-specific client
        self.client = self._initialize_client()

    def analyze_screenshot(
        self,
        image_path: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Analyze screenshot using vision model to extract book information.

        Args:
            image_path: Path to the screenshot image file
            prompt: The prompt template for vision analysis
            model: Optional model override (uses config default if None)
            max_tokens: Maximum tokens for the response (default: 4000)

        Returns:
            A dictionary containing:
                - books: List of extracted book dictionaries with title, author, reading_status
                - confidence: Confidence score for the extraction (0.0-1.0)
                - raw_response: Raw text response from the LLM

        Example:
            {
                "books": [
                    {
                        "title": "The Way of Kings",
                        "author": "Brandon Sanderson",
                        "reading_status": "want-to-read"
                    },
                    ...
                ],
                "confidence": 0.95,
                "raw_response": "..."
            }

        Raises:
            FileNotFoundError: If the image file does not exist
            ValueError: If the image format is not supported
            anthropic.APIError: If the API request fails
            json.JSONDecodeError: If the response cannot be parsed as JSON
        """
        # Validate image file exists
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Encode image to base64
        base64_image, media_type = self._encode_image(image_path)

        # Use provided model or default from config
        model_name = model or self.default_model

        try:
            # Make API request to Anthropic
            response = self.client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Extract text response
            raw_response = response.content[0].text

            # Parse JSON response from LLM
            parsed_data = self._parse_llm_response(raw_response)

            return parsed_data

        except anthropic.APIError as e:
            raise anthropic.APIError(
                f"Anthropic API request failed: {e}"
            )
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Failed to parse LLM response as JSON: {e.msg}",
                e.doc,
                e.pos
            )

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """
        Encode image file to base64 and determine media type.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (base64_encoded_data, media_type)

        Raises:
            ValueError: If image format is not supported
        """
        # Determine media type from file extension
        file_extension = Path(image_path).suffix.lower()
        media_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }

        media_type = media_type_map.get(file_extension)
        if not media_type:
            raise ValueError(
                f"Unsupported image format: {file_extension}. "
                f"Supported formats: {', '.join(media_type_map.keys())}"
            )

        # Read and encode image
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_encoded = base64.b64encode(image_data).decode('utf-8')

        return base64_encoded, media_type

    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse LLM response text into structured data.

        Args:
            raw_response: Raw text response from LLM

        Returns:
            Dictionary with books, confidence, and raw_response

        Raises:
            json.JSONDecodeError: If response cannot be parsed as JSON
        """
        # Try to parse as JSON
        try:
            parsed = json.loads(raw_response)

            # Ensure required fields exist
            if "books" not in parsed:
                parsed["books"] = []

            if "confidence" not in parsed:
                parsed["confidence"] = 0.0

            # Add raw response for debugging
            parsed["raw_response"] = raw_response

            return parsed

        except json.JSONDecodeError:
            # If not valid JSON, return error structure
            return {
                "books": [],
                "confidence": 0.0,
                "raw_response": raw_response,
                "error": "Failed to parse response as JSON"
            }

    def _initialize_client(self):
        """
        Initialize provider-specific client.

        Returns:
            The initialized client object for the specified provider

        Raises:
            ValueError: If the provider is not supported or API key is missing
        """
        if self.provider == "anthropic":
            if not self.api_key:
                raise ValueError(
                    "Anthropic API key not found. "
                    "Please ensure 'anthropic_api_key' is set in secrets.json"
                )
            return anthropic.Anthropic(api_key=self.api_key)

        # Future: Add OpenAI, Google, etc.
        raise ValueError(f"Unsupported provider: {self.provider}")

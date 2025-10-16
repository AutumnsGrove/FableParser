"""
LLM Inference abstraction layer for vision analysis.

This module provides a unified interface for making LLM API calls,
currently supporting Anthropic's Claude with vision capabilities.
Future support for OpenAI, Google, and other providers can be added here.
"""

from typing import Optional, Dict, Any


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
        """
        self.provider = provider
        self.api_key = None  # Will be loaded from secrets_handler
        self.client = None  # Will be initialized via _initialize_client()

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
        """
        pass

    def _initialize_client(self):
        """
        Initialize provider-specific client.

        Returns:
            The initialized client object for the specified provider

        Raises:
            ValueError: If the provider is not supported
        """
        if self.provider == "anthropic":
            # import anthropic
            # return anthropic.Anthropic(api_key=self.api_key)
            pass
        # Future: Add OpenAI, Google, etc.
        raise ValueError(f"Unsupported provider: {self.provider}")

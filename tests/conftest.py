"""
Pytest configuration file for FableParser tests.

This file ensures that the project root is in the Python path
so that imports work correctly during testing.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

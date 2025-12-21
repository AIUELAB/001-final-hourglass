"""
pytest configuration file.

This file is automatically loaded by pytest before running tests.
It adds the src/ directory to the Python path so that tests can import modules.
"""

import sys
from pathlib import Path

# Add src/ to Python path for test imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Also add project root for imports like 'from src.xxx import yyy'
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

#!/usr/bin/env python3
"""
Top-level entrypoint for code-check.
Delegates to modular code_check package.
"""

import sys
from pathlib import Path

# Ensure code_check package is on sys.path
package_dir = Path(__file__).resolve().parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

from code_check.cli import main

if __name__ == "__main__":
    main()

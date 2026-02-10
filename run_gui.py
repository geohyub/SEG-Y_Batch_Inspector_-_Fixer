#!/usr/bin/env python3
"""SEG-Y Batch Inspector & Fixer - GUI Launcher."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from segy_toolbox.gui.app import main

if __name__ == "__main__":
    main()

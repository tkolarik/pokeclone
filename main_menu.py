#!/usr/bin/env python3
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.main_menu import main


if __name__ == "__main__":
    main()

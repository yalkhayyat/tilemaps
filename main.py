#!/usr/bin/env python3
import sys
import os

# Ensure src is in the python path
# Ensure project root is in the python path to allow 'from src...' imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core import generation

if __name__ == "__main__":
    generation.main(generation.parser.parse_args())

"""
main.py — Pygbag/WASM entry point for the web build.

For local desktop play, run src/StageController.py directly as before.
Pygbag requires this file at the project root with an async def main().
"""

import sys
import os

# Allow imports from src/ without changing any existing source files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import asyncio
import random

# WASM has no OS entropy by default — seed explicitly before any random calls
random.seed(os.urandom(16))

import StageController


async def main():
    # StageController.main() will be made async as part of the async cascade.
    # For now this wraps the synchronous call so pygbag can find the entry point.
    StageController.main(0, 0)

asyncio.run(main())

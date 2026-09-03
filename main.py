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

import pygame
try:
    platform.window.console.log(f"main.py pygame file: {getattr(pygame, '__file__', 'no __file__')}")
    platform.window.console.log(f"main.py pygame dir: {dir(pygame)}")
except Exception:
    pass

import StageController


import platform

try:
    platform.window.console.log("main.py: module level executing")
except Exception:
    pass

async def main():
    try:
        platform.window.console.log("main.py: main() async started!")
    except Exception:
        pass
    print("=== EXPLORERS WEB STARTED ===")
    try:
        await StageController.main(0, 0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            platform.window.console.error(f"StageController error: {e}")
        except Exception:
            pass

try:
    platform.window.console.log("main.py: calling asyncio.run(main())")
except Exception:
    pass

asyncio.run(main())

try:
    platform.window.console.log("main.py: asyncio.run(main()) call complete")
except Exception:
    pass

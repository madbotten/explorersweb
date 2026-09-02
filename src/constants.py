"""
constants.py — shared game-wide constants.

Import with:
    from constants import TOP_BAR_Y, DEBUG
"""

# ---------------------------------------------------------------------------
# Debug flag
# Set to True to enable verbose in-game console output (stat checks, rolls,
# stealth results, interaction outcomes, battle events, etc.)
# ---------------------------------------------------------------------------
DEBUG = False

# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------

# Y pixel position of the top navigation bar (PROCEED / EXIT buttons, day /
# stage text). Applies consistently across all game screens.
TOP_BAR_Y = 4

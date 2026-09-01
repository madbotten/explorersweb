"""
Explorers unit tests — run with:
    .venv/bin/python -m unittest gametests.TestHealthMorale -v
    .venv/bin/python -m unittest discover -v
"""
import os
import sys
import unittest

# Run pygame headlessly (no display required)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Add src to path so we can import game modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pygame
pygame.init()

from Character import Character


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_human(strength=50, willpower=50, morale=100):
    """Create a minimal team-type character with controlled stats."""
    c = Character(1, "team")
    c.stats["strength"]   = strength
    c.stats["willpower"]  = willpower
    c.stats["max_health"] = strength + willpower   # re-derive after override
    c.current_health      = c.stats["max_health"]
    c.morale              = morale
    return c


def make_robot(max_life=200, morale=100):
    """Create a minimal robot character with controlled HP."""
    c = Character(1, "robot")
    c.max_life                = max_life
    c.stats["max_health"]     = max_life
    c.current_health          = max_life
    c.morale                  = morale
    return c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealthMorale(unittest.TestCase):

    # ---- Initial state -------------------------------------------------

    def test_human_starts_full_health(self):
        c = make_human(50, 50)
        self.assertEqual(c.current_health, 100)

    def test_human_max_health_is_strength_plus_willpower(self):
        c = make_human(60, 40)
        self.assertEqual(c.stats["max_health"], 100)

    def test_human_starts_full_morale(self):
        c = make_human()
        self.assertEqual(c.morale, 100)

    def test_robot_starts_full_health(self):
        r = make_robot(200)
        self.assertEqual(r.current_health, 200)

    def test_robot_starts_morale_100(self):
        r = make_robot(200)
        self.assertEqual(r.morale, 100)

    # ---- Morale bounds -------------------------------------------------

    def test_demoralize_clamps_to_zero(self):
        c = make_human()
        c.demoralize(200)
        self.assertEqual(c.morale, 0)

    def test_encourage_clamps_to_100(self):
        c = make_human(morale=80)
        c.encourage(50)
        self.assertEqual(c.morale, 100)

    def test_morale_never_negative(self):
        c = make_human(morale=5)
        c.demoralize(10)
        self.assertGreaterEqual(c.morale, 0)

    # ---- Robots immune to social morale --------------------------------

    def test_robot_immune_to_demoralize(self):
        r = make_robot()
        r.demoralize(50)
        self.assertEqual(r.morale, 100)   # unchanged

    def test_robot_immune_to_encourage(self):
        r = make_robot()
        r.morale = 40
        r.encourage(30)
        self.assertEqual(r.morale, 40)    # unchanged

    # ---- hurt() --------------------------------------------------------

    def test_hurt_reduces_current_health_not_max(self):
        c = make_human(50, 50)   # max_health = 100
        c.hurt(20, "impact")
        self.assertEqual(c.stats["max_health"], 100)  # stat unchanged
        self.assertEqual(c.current_health, 80)

    def test_hurt_minimum_1_damage(self):
        c = make_human(50, 50)
        before = c.current_health
        c.hurt(0, "impact")
        self.assertEqual(c.current_health, before - 1)

    def test_hurt_morale_proportional_to_max_health(self):
        # 15 damage vs max_health=100 -> morale drop = round(15/100*100) = 15
        c = make_human(50, 50)   # max_health = 100
        c.hurt(15, "impact")
        # morale drops by 15, also clamped to health_pct (85%)
        self.assertEqual(c.morale, 85)   # 100 - 15 = 85, health_pct = 85

    def test_hurt_morale_proportional_scales_with_max_health(self):
        # 15 damage vs max_health=200 -> morale drop = round(15/200*100) = 8
        c = make_human(100, 100)  # max_health = 200
        c.hurt(15, "impact")
        expected_drop  = round(15 / 200 * 100)    # = 8
        expected_morale = min(100 - expected_drop, c.health_pct())
        self.assertEqual(c.morale, expected_morale)

    def test_hurt_morale_cannot_exceed_health_pct(self):
        c = make_human(50, 50, morale=30)
        c.hurt(5, "impact")
        self.assertLessEqual(c.morale, c.health_pct())

    def test_hurt_kills_when_health_reaches_zero(self):
        c = make_human(50, 50)
        died = c.hurt(200, "impact")
        self.assertTrue(died)
        self.assertEqual(c.current_health, 0)

    def test_hurt_does_not_kill_on_partial_damage(self):
        c = make_human(50, 50)
        died = c.hurt(10, "impact")
        self.assertFalse(died)

    def test_robot_hurt_sets_morale_to_health_pct(self):
        r = make_robot(200)
        r.hurt(50, "impact")
        expected_hp  = 200 - 50
        expected_pct = int(expected_hp / 200 * 100)
        self.assertEqual(r.current_health, expected_hp)
        self.assertEqual(r.morale, expected_pct)

    def test_robot_hurt_does_not_exceed_100_morale(self):
        r = make_robot(200)
        r.hurt(1, "impact")
        self.assertLessEqual(r.morale, 100)

    # ---- is_alive / health_pct -----------------------------------------

    def test_is_alive_true_when_health_positive(self):
        c = make_human()
        self.assertTrue(c.is_alive())

    def test_is_alive_false_when_health_zero(self):
        c = make_human()
        c.current_health = 0
        self.assertFalse(c.is_alive())

    def test_health_pct_full(self):
        c = make_human(50, 50)
        self.assertEqual(c.health_pct(), 100)

    def test_health_pct_partial(self):
        c = make_human(50, 50)
        c.current_health = 50
        self.assertEqual(c.health_pct(), 50)

    def test_health_pct_zero(self):
        c = make_human()
        c.current_health = 0
        self.assertEqual(c.health_pct(), 0)

    # ---- get_health_ratio ----------------------------------------------

    def test_get_health_ratio_human_full(self):
        c = make_human(50, 50)
        self.assertAlmostEqual(c.get_health_ratio(), 1.0)

    def test_get_health_ratio_human_half(self):
        c = make_human(50, 50)
        c.current_health = 50
        self.assertAlmostEqual(c.get_health_ratio(), 0.5)

    def test_get_health_ratio_robot_full(self):
        r = make_robot(200)
        self.assertAlmostEqual(r.get_health_ratio(), 1.0)

    def test_get_health_ratio_robot_half(self):
        r = make_robot(200)
        r.current_health = 100
        self.assertAlmostEqual(r.get_health_ratio(), 0.5)

    # ---- morale_from_health --------------------------------------------

    def test_morale_from_health_raises_human_morale_to_health_pct(self):
        c = make_human(50, 50, morale=30)
        c.current_health = 80   # health_pct = 80
        c.morale_from_health()
        self.assertEqual(c.morale, 80)

    def test_morale_from_health_does_not_lower_human_morale(self):
        c = make_human(50, 50, morale=90)
        c.current_health = 80   # health_pct = 80, morale already above
        c.morale_from_health()
        self.assertEqual(c.morale, 90)   # stays at 90

    def test_morale_from_health_sets_robot_morale_exactly(self):
        r = make_robot(200)
        r.current_health = 100   # 50% health
        r.morale = 90
        r.morale_from_health()
        self.assertEqual(r.morale, 50)

    def test_morale_from_health_caps_at_100(self):
        c = make_human(50, 50, morale=99)
        c.current_health = 100
        c.morale_from_health()
        self.assertLessEqual(c.morale, 100)

    # ---- max_health stat unchanged by damage/healing -------------------

    def test_max_health_stat_unchanged_by_damage(self):
        c = make_human(50, 50)
        original_max = c.stats["max_health"]
        c.hurt(30, "impact")
        self.assertEqual(c.stats["max_health"], original_max)

    def test_robot_max_life_unchanged_by_damage(self):
        r = make_robot(200)
        r.hurt(50, "impact")
        self.assertEqual(r.max_life, 200)


if __name__ == "__main__":
    unittest.main()

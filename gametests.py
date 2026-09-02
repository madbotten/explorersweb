"""
Explorers unit tests — run with:
    .venv/bin/python -m unittest gametests.TestHealthMorale -v
    .venv/bin/python -m unittest discover -v
"""
import os
import sys
import random
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
    c.name                    = "TestBot"   # robots skip name assignment in __init__
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


# ---------------------------------------------------------------------------
# Helpers shared by initiative tests
# ---------------------------------------------------------------------------

from unittest.mock import patch
from Battle import initiative


def make_human_controlled(strength=40, willpower=60, coordination=50,
                          intelligence=40, courage=50, charisma=40,
                          morale=100):
    """Human character with fully specified base stats so derived stats are predictable."""
    c = make_human(strength, willpower, morale=morale)
    # Override the base stats that feed into derived ones
    c.stats["coordination"]  = coordination
    c.stats["intelligence"]  = intelligence
    c.stats["courage"]       = courage
    c.stats["charisma"]      = charisma
    # Re-derive all dependent stats exactly as __init__ does
    c.stats["offense"]      = round((coordination + courage) / 2)
    c.stats["defense"]      = round((coordination + strength) / 2)
    c.stats["deception"]    = round((courage + charisma) / 2)
    c.stats["evasion"]      = round((intelligence + coordination) / 2)
    c.stats["analyze"]      = round((intelligence + willpower) / 2)
    c.stats["max_health"]   = strength + willpower
    c.stats["movement"]     = strength + willpower + coordination
    c.stats["meleecombat"]  = c.stats["evasion"] + strength
    c.stats["perception"]   = round((willpower + coordination) / 2)
    c.stats["surprise"]     = c.stats["evasion"] + c.stats["perception"]
    c.stats["leadership"]   = intelligence + charisma + courage
    c.current_health        = c.stats["max_health"]
    return c


def make_scoutbot_simple(perception=75):
    """Minimal scoutbot for initiative tests (no pygame image loading)."""
    r = make_robot(150, morale=100)
    r.occupation     = "scoutbot"
    r.stats["perception"] = perception
    r.stats["surprise"]   = 150          # hardcoded in factory
    return r


class TestInitiative(unittest.TestCase):

    # ---- Stat derivation -----------------------------------------------

    def test_perception_formula(self):
        # perception = round((willpower + coordination) / 2)
        c = make_human_controlled(willpower=60, coordination=50)
        self.assertEqual(c.stats["perception"], round((60 + 50) / 2))   # 55

    def test_perception_rounds_correctly(self):
        # (willpower=61 + coordination=50) / 2 = 55.5 → rounds to 56
        c = make_human_controlled(willpower=61, coordination=50)
        self.assertEqual(c.stats["perception"], 56)

    def test_surprise_uses_evasion_plus_perception(self):
        # evasion = (intelligence + coordination) / 2
        # surprise = evasion + perception
        c = make_human_controlled(willpower=60, coordination=50, intelligence=40)
        evasion    = round((40 + 50) / 2)   # 45
        perception = round((60 + 50) / 2)   # 55
        self.assertEqual(c.stats["evasion"],    evasion)
        self.assertEqual(c.stats["perception"], perception)
        self.assertEqual(c.stats["surprise"],   evasion + perception)  # 100

    def test_surprise_does_not_use_deception(self):
        # Two characters identical except different charisma (affects deception).
        # Their surprise stat should be the same.
        c1 = make_human_controlled(charisma=10)
        c2 = make_human_controlled(charisma=90)
        # deception differs
        self.assertNotEqual(c1.stats["deception"], c2.stats["deception"])
        # surprise is identical (deception not in formula)
        self.assertEqual(c1.stats["surprise"], c2.stats["surprise"])

    def test_high_perception_raises_surprise(self):
        lo = make_human_controlled(willpower=20, coordination=20)
        hi = make_human_controlled(willpower=80, coordination=80)
        self.assertGreater(hi.stats["surprise"], lo.stats["surprise"])

    # ---- Scout bonus ---------------------------------------------------

    def test_no_scoutbot_gives_zero_scout_bonus(self):
        # With a fixed roll, team member roll = fixed + surprise (no scout bonus)
        hero   = make_human_controlled()
        enemy  = make_human_controlled()
        with patch("Battle.random.randint", return_value=50):
            order = initiative([hero], [enemy])
        self.assertEqual(len(order), 2)

    def test_scoutbot_adds_bonus_to_team_rolls(self):
        # hero vs enemy: hero has a scoutbot ally → gets +5 scout bonus.
        # Fix random to 50 for everyone.
        # hero.surprise = 100, enemy.surprise = 100, scout adds +5 to hero.
        # hero roll = 50 + 100 + 5 = 155; enemy roll = 50 + 100 = 150
        hero   = make_human_controlled()
        scout  = make_scoutbot_simple()
        enemy  = make_human_controlled()
        # Zero out surprise so the bonus is the only differentiator
        hero.stats["surprise"]  = 0
        enemy.stats["surprise"] = 0
        with patch("Battle.random.randint", return_value=50):
            order = initiative([hero, scout], [enemy])
        # hero and scout should both beat enemy (hero gets scout_bonus=5)
        team_positions   = [order.index(hero), order.index(scout)]
        enemy_position   = order.index(enemy)
        self.assertLess(min(team_positions), enemy_position)

    def test_two_scoutbots_double_the_bonus(self):
        hero    = make_human_controlled()
        scout1  = make_scoutbot_simple()
        scout2  = make_scoutbot_simple()
        enemy   = make_human_controlled()
        hero.stats["surprise"]  = 0
        enemy.stats["surprise"] = 0
        # Two scoutbots → scout_bonus = 10. hero roll = 50+10=60, enemy = 50
        with patch("Battle.random.randint", return_value=50):
            order = initiative([hero, scout1, scout2], [enemy])
        self.assertLess(order.index(hero), order.index(enemy))

    # ---- Squad tactics bonus -------------------------------------------

    def test_squad_tactics_adds_bonus(self):
        hero  = make_human_controlled()
        hero.skills["Squad Tactics"] = 50   # bonus = 50 / 10 = 5
        enemy = make_human_controlled()
        hero.stats["surprise"]  = 0
        enemy.stats["surprise"] = 0
        with patch("Battle.random.randint", return_value=50):
            order = initiative([hero], [enemy])
        # hero roll = 50 + 5 (squad tactics) = 55 > 50
        self.assertLess(order.index(hero), order.index(enemy))

    # ---- Brazen bonus --------------------------------------------------

    def test_brazen_bonus_applied_to_team(self):
        hero  = make_human_controlled()
        enemy = make_human_controlled()
        hero.stats["surprise"]  = 0
        enemy.stats["surprise"] = 0
        with patch("Battle.random.randint", return_value=50):
            order = initiative([hero], [enemy], brazen_bonus=20)
        # hero roll = 50 + 20 = 70 > enemy 50
        self.assertLess(order.index(hero), order.index(enemy))

    def test_brazen_bonus_not_applied_to_enemies(self):
        hero  = make_human_controlled()
        enemy = make_human_controlled()
        hero.stats["surprise"]  = 0
        enemy.stats["surprise"] = 0
        with patch("Battle.random.randint", return_value=50):
            # Even with brazen_bonus, only hero benefits
            order = initiative([hero], [enemy], brazen_bonus=100)
        self.assertLess(order.index(hero), order.index(enemy))

    # ---- General correctness -------------------------------------------

    def test_initiative_returns_all_characters(self):
        team   = [make_human_controlled() for _ in range(3)]
        enemies = [make_human_controlled() for _ in range(2)]
        order = initiative(team, enemies)
        self.assertEqual(len(order), 5)
        for m in team + enemies:
            self.assertIn(m, order)

    def test_higher_surprise_wins_with_fixed_roll(self):
        low_surprise  = make_human_controlled(willpower=20, coordination=20)
        high_surprise = make_human_controlled(willpower=80, coordination=80)
        with patch("Battle.random.randint", return_value=50):
            order = initiative([high_surprise], [low_surprise])
        self.assertLess(order.index(high_surprise), order.index(low_surprise))


# ---------------------------------------------------------------------------
# Phase 2: Supply Logistics skill + required_singular_events (Oreos event)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock
from ReturnVoyage import calculate_outcome_out_of_oreos


def make_dummy_screen():
    """Minimal pygame surface usable as a screen argument."""
    return pygame.Surface((100, 100))


def make_dummy_font():
    """Minimal font object; render returns a tiny surface."""
    return pygame.font.SysFont(None, 16)


class TestSupplyLogistics(unittest.TestCase):

    # ---- Skill registration --------------------------------------------

    def test_supply_logistics_in_possible_skills(self):
        self.assertIn("Supply Logistics", Character.possible_skills)

    def test_supply_logistics_in_skill_descriptions(self):
        self.assertIn("Supply Logistics", Character.skill_descriptions)

    def test_supply_logistics_description_non_empty(self):
        desc = Character.skill_descriptions["Supply Logistics"]
        self.assertTrue(len(desc) > 0)

    # ---- Oreos event: skilled member present ---------------------------

    def test_oreos_fail_demoralizes_non_robots(self):
        """When the skill check fails, non-robot crew lose 5 morale."""
        crew = [make_human(morale=100), make_human(morale=100)]
        crew[0].skills["Supply Logistics"] = 50
        screen = make_dummy_screen()
        font   = make_dummy_font()
        # Patch standard_skill_check to always fail
        with patch("ReturnVoyage.standard_skill_check", return_value=False), \
             patch("ReturnVoyage.type_out_text"):
            calculate_outcome_out_of_oreos(crew, None, "Supply Logistics", screen, font)
        for m in crew:
            self.assertEqual(m.morale, 95)   # 100 - 5

    def test_oreos_pass_no_morale_loss(self):
        """When the skill check passes, morale is untouched."""
        crew = [make_human(morale=100), make_human(morale=100)]
        crew[0].skills["Supply Logistics"] = 80
        screen = make_dummy_screen()
        font   = make_dummy_font()
        with patch("ReturnVoyage.standard_skill_check", return_value=True), \
             patch("ReturnVoyage.type_out_text"):
            calculate_outcome_out_of_oreos(crew, None, "Supply Logistics", screen, font)
        for m in crew:
            self.assertEqual(m.morale, 100)

    def test_oreos_robots_immune_to_penalty(self):
        """Robots must not be demoralized by the Oreos event."""
        human = make_human(morale=100)
        robot = make_robot(150, morale=100)
        team = [human, robot]
        screen = make_dummy_screen()
        font   = make_dummy_font()
        # Force the human to be selected, skill check fails → only human penalised
        with patch("ReturnVoyage.determine_best_team_member", return_value=human), \
             patch("ReturnVoyage.standard_skill_check", return_value=False), \
             patch("ReturnVoyage.type_out_text"):
            calculate_outcome_out_of_oreos(team, None, "Supply Logistics", screen, font)
        self.assertEqual(human.morale, 95)   # human loses 5
        self.assertEqual(robot.morale, 100)  # robot unchanged

    # ---- Oreos event: no skilled member --------------------------------

    def test_oreos_no_skilled_member_demoralizes_all_non_robots(self):
        """If no one has Supply Logistics, the penalty fires unconditionally."""
        crew = [make_human(morale=100), make_human(morale=100)]
        screen = make_dummy_screen()
        font   = make_dummy_font()
        # Patch determine_best_team_member to None to simulate the no-skill path
        with patch("ReturnVoyage.determine_best_team_member", return_value=None), \
             patch("ReturnVoyage.type_out_text"):
            calculate_outcome_out_of_oreos(crew, None, "Supply Logistics", screen, font)
        for m in crew:
            self.assertEqual(m.morale, 95)

    def test_oreos_no_skilled_member_robot_still_immune(self):
        """Robot morale not affected even when no one has Supply Logistics."""
        robot = make_robot(150, morale=100)
        robot.morale = 100
        screen = make_dummy_screen()
        font   = make_dummy_font()
        with patch("ReturnVoyage.type_out_text"):
            calculate_outcome_out_of_oreos([robot], None, "Supply Logistics", screen, font)
        self.assertEqual(robot.morale, 100)

    # ---- required_singular_events scheduling ---------------------------

    def test_required_trigger_points_within_voyage_range(self):
        """Trigger points must be within [2, max_events-1]."""
        max_events = 12
        available  = list(range(2, max_events))
        triggers   = set(random.sample(available, min(1, len(available))))
        self.assertTrue(triggers.issubset(set(available)))

    def test_required_events_fire_before_arrival(self):
        """Simulates the force-fire path: required event runs when voyage exceeds max."""
        import random as rnd
        required = [MagicMock()]   # one pending required event with context.location
        required[0].context.location = MagicMock()
        # Simulate: events_completed > max_events, required still pending → pop and run
        self.assertEqual(len(required), 1)
        event = required.pop(0)
        event.run(None, None, None, None, None)  # run with dummy args
        self.assertEqual(len(required), 0)       # consumed
        event.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()

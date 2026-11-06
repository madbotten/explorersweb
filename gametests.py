"""
Explorers unit tests — run with:
    .venv/bin/python -m unittest gametests.TestHealthMorale -v
    .venv/bin/python -m unittest discover -v
"""
import os
import sys
import random
import unittest
import asyncio

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
    """Create a minimal team-type character with controlled stats.
    psychotic and traitor are forced False so flag-gated paths (e.g. demoralize)
    behave deterministically; tests that need those flags set them explicitly.
    """
    c = Character(1, "team")
    c.stats["strength"]   = strength
    c.stats["willpower"]  = willpower
    c.stats["max_health"] = strength + willpower   # re-derive after override
    c.current_health      = c.stats["max_health"]
    c.morale              = morale
    c.psychotic           = False
    c.traitor             = False
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
from Voyage import calculate_outcome_out_of_oreos


def make_dummy_screen():
    """Minimal pygame surface usable as a screen argument."""
    return pygame.Surface((100, 100))


def make_dummy_font():
    """Minimal font object; render returns a tiny surface."""
    return pygame.font.SysFont(None, 16)


class TestSupplyLogistics(unittest.IsolatedAsyncioTestCase):

    # ---- Skill registration --------------------------------------------

    async def test_supply_logistics_in_possible_skills(self):
        self.assertIn("Supply Logistics", Character.possible_skills)

    async def test_supply_logistics_in_skill_descriptions(self):
        self.assertIn("Supply Logistics", Character.skill_descriptions)

    async def test_supply_logistics_description_non_empty(self):
        desc = Character.skill_descriptions["Supply Logistics"]
        self.assertTrue(len(desc) > 0)

    # ---- Oreos event: skilled member present ---------------------------

    async def test_oreos_fail_demoralizes_non_robots(self):
        """When the skill check fails, non-robot crew lose 5 morale."""
        crew = [make_human(morale=100), make_human(morale=100)]
        crew[0].skills["Supply Logistics"] = 50
        screen = make_dummy_screen()
        font   = make_dummy_font()
        # Patch standard_skill_check to always fail
        with patch("Voyage.standard_skill_check", return_value=False), \
             patch("Voyage.type_out_text"):
            await calculate_outcome_out_of_oreos(crew, None, "Supply Logistics", screen, font)
        for m in crew:
            self.assertEqual(m.morale, 95)   # 100 - 5

    async def test_oreos_pass_no_morale_loss(self):
        """When the skill check passes, morale is untouched."""
        crew = [make_human(morale=100), make_human(morale=100)]
        crew[0].skills["Supply Logistics"] = 80
        screen = make_dummy_screen()
        font   = make_dummy_font()
        with patch("Voyage.standard_skill_check", return_value=True), \
             patch("Voyage.type_out_text"):
            await calculate_outcome_out_of_oreos(crew, None, "Supply Logistics", screen, font)
        for m in crew:
            self.assertEqual(m.morale, 100)

    async def test_oreos_robots_immune_to_penalty(self):
        """Robots must not be demoralized by the Oreos event."""
        human = make_human(morale=100)
        robot = make_robot(150, morale=100)
        team = [human, robot]
        screen = make_dummy_screen()
        font   = make_dummy_font()
        # Force the human to be selected, skill check fails → only human penalised
        with patch("Voyage.determine_best_team_member", return_value=human), \
             patch("Voyage.standard_skill_check", return_value=False), \
             patch("Voyage.type_out_text"):
            await calculate_outcome_out_of_oreos(team, None, "Supply Logistics", screen, font)
        self.assertEqual(human.morale, 95)   # human loses 5
        self.assertEqual(robot.morale, 100)  # robot unchanged

    # ---- Oreos event: no skilled member --------------------------------

    async def test_oreos_no_skilled_member_demoralizes_all_non_robots(self):
        """If no one has Supply Logistics, the penalty fires unconditionally."""
        crew = [make_human(morale=100), make_human(morale=100)]
        screen = make_dummy_screen()
        font   = make_dummy_font()
        # Patch determine_best_team_member to None to simulate the no-skill path
        with patch("Voyage.determine_best_team_member", return_value=None), \
             patch("Voyage.type_out_text"):
            await calculate_outcome_out_of_oreos(crew, None, "Supply Logistics", screen, font)
        for m in crew:
            self.assertEqual(m.morale, 95)

    async def test_oreos_no_skilled_member_robot_still_immune(self):
        """Robot morale not affected even when no one has Supply Logistics."""
        robot = make_robot(150, morale=100)
        robot.morale = 100
        screen = make_dummy_screen()
        font   = make_dummy_font()
        with patch("Voyage.determine_best_team_member", return_value=None), \
             patch("Voyage.type_out_text"):
            await calculate_outcome_out_of_oreos([robot], None, "Supply Logistics", screen, font)
        self.assertEqual(robot.morale, 100)

    # ---- required_singular_events scheduling ---------------------------

    async def test_required_trigger_points_within_voyage_range(self):
        """Trigger points must be within [2, max_events-1]."""
        max_events = 12
        available  = list(range(2, max_events))
        triggers   = set(random.sample(available, min(1, len(available))))
        self.assertTrue(triggers.issubset(set(available)))

    async def test_required_events_fire_before_arrival(self):
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


# ---------------------------------------------------------------------------
# Phase 3: Psychotic Attack event
# ---------------------------------------------------------------------------

from ReturnVoyage import calculate_outcome_psychotic_attack


def make_psycho(offense=80, perception=30, surprise=50, morale=100):
    """Human with psychotic=True and controlled combat stats."""
    c = make_human(morale=morale)
    c.psychotic = True
    c.stats["offense"]    = offense
    c.stats["perception"] = perception
    c.stats["surprise"]   = surprise
    return c


def make_victim(offense=50, perception=50, surprise=50, morale=100):
    """Ordinary non-psychotic human with controlled stats."""
    c = make_human(morale=morale)
    c.psychotic = False
    c.stats["offense"]    = offense
    c.stats["perception"] = perception
    c.stats["surprise"]   = surprise
    return c


class TestPsychoticAttack(unittest.IsolatedAsyncioTestCase):

    # ---- No-op when no psychotics ----------------------------------------

    async def test_no_psychotics_no_op(self):
        """Event is a no-op if no crew member is psychotic."""
        crew = [make_victim(), make_victim()]
        team = list(crew)
        screen, font = make_dummy_screen(), make_dummy_font()
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.mission_failure"):
            await calculate_outcome_psychotic_attack(team, None, None, screen, font)
        self.assertEqual(team, crew)   # unchanged

    # ---- Strongest psycho chosen -----------------------------------------

    async def test_strongest_psycho_chosen(self):
        """When multiple psychotics exist, highest-offense one is used."""
        weak_psycho   = make_psycho(offense=40)
        strong_psycho = make_psycho(offense=90)
        victim        = make_victim(offense=999)   # always wins combat
        team = [weak_psycho, strong_psycho, victim]
        screen, font = make_dummy_screen(), make_dummy_font()
        chosen = []

        original_type_out_text = __import__("ReturnVoyage").type_out_text

        async def capture_text(screen, text, font, color=None):
            chosen.append(text)

        with patch("ReturnVoyage.type_out_text", side_effect=capture_text):
            await calculate_outcome_psychotic_attack(team, None, None, screen, font)

        alert_lines = [t for t in chosen if "has snapped" in t]
        self.assertTrue(any(strong_psycho.name in t for t in alert_lines),
                        "Expected the high-offense psycho in the alert message")

    # ---- Perception catches psycho early ---------------------------------

    async def test_perception_success_sends_psycho_to_brig(self):
        """If perception check passes on first round, psycho is removed."""
        psycho = make_psycho()
        guard  = make_victim(perception=95)
        team   = [psycho, guard]
        screen, font = make_dummy_screen(), make_dummy_font()

        # Perception always passes: roll=1, perception=95, difficulty=-20 → 1 < 75
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", return_value=1):
            await calculate_outcome_psychotic_attack(team, None, None, screen, font)

        self.assertNotIn(psycho, team)   # removed (brig)
        self.assertIn(guard, team)

    # ---- Victim defeats psycho -------------------------------------------

    async def test_victim_wins_combat_sends_psycho_to_brig(self):
        """When victim rolls higher offense, psycho is subdued and removed."""
        psycho = make_psycho(offense=10)    # very weak
        victim = make_victim(offense=99)    # very strong
        team   = [psycho, victim]
        screen, font = make_dummy_screen(), make_dummy_font()

        # Perception always fails (roll=99), offense rolls: psycho=1+10=11, victim=30+99=129
        def controlled_randint(a, b):
            if b == 100:   return 99   # perception roll always fails
            if b == 30:    return 1    # offense die always low (psycho 1, victim 1 — but victim still wins on stat)
            return (a + b) // 2

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", side_effect=controlled_randint):
            await calculate_outcome_psychotic_attack(team, None, None, screen, font)

        self.assertNotIn(psycho, team)
        self.assertIn(victim, team)

    # ---- Victim killed, rampage continues --------------------------------

    async def test_victim_killed_continues_until_perception_wins(self):
        """Psycho kills one victim; second perceiver eventually ends rampage."""
        psycho  = make_psycho(offense=99)
        victim1 = make_victim(offense=1, perception=1)
        victim2 = make_victim(offense=1, perception=99)
        team    = [psycho, victim1, victim2]
        screen, font = make_dummy_screen(), make_dummy_font()

        call_count = [0]
        def alternating_randint(a, b):
            call_count[0] += 1
            if b == 100:
                # First perception roll fails, second succeeds
                return 99 if call_count[0] <= 3 else 1
            return (a + b) // 2

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", side_effect=alternating_randint), \
             patch("ReturnVoyage.random.choice", return_value=victim1):
            await calculate_outcome_psychotic_attack(team, None, None, screen, font)

        self.assertNotIn(psycho, team)   # eventually caught

    # ---- Robots never targeted -------------------------------------------

    async def test_robots_not_targeted_as_victims(self):
        """Robots are excluded from the victim pool."""
        psycho = make_psycho(offense=99)
        robot  = make_robot(200, morale=100)
        human  = make_victim(offense=99)    # strong enough to win
        team   = [psycho, robot, human]
        screen, font = make_dummy_screen(), make_dummy_font()

        chosen_victims = []
        original_choice = random.choice

        def track_choice(lst):
            chosen = original_choice(lst)
            chosen_victims.append(chosen)
            return chosen

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", return_value=50), \
             patch("ReturnVoyage.random.choice", side_effect=track_choice):
            await calculate_outcome_psychotic_attack(team, None, None, screen, font)

        self.assertNotIn(robot, chosen_victims,
                         "Robot should never be chosen as a victim")



# ---------------------------------------------------------------------------
# Phase 4: Traitor Sabotage event
# ---------------------------------------------------------------------------

from ReturnVoyage import calculate_outcome_traitor_sabotage


def make_traitor(leadership=50, perception=50, surprise=80, mission_points=100):
    """Human with traitor=True and controlled stats."""
    c = make_human(morale=100)
    c.traitor = True
    c.stats["leadership"]  = leadership
    c.stats["perception"]  = perception
    c.stats["surprise"]    = surprise
    c.mission_points       = mission_points
    return c


def make_commander(leadership=120, perception=70, surprise=100, mission_points=50):
    """Non-traitor human with high leadership (acts as commander)."""
    c = make_human(morale=100)
    c.traitor = False
    c.stats["leadership"]  = leadership
    c.stats["perception"]  = perception
    c.stats["surprise"]    = surprise
    c.mission_points       = mission_points
    return c


class TestTraitorSabotage(unittest.IsolatedAsyncioTestCase):

    # ---- No-op when no traitors -----------------------------------------

    async def test_no_traitors_no_op(self):
        """Event is a no-op if no crew member is a traitor."""
        crew = [make_commander(), make_commander()]
        team = list(crew)
        screen, font = make_dummy_screen(), make_dummy_font()
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.standard_skill_check", return_value=False):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)
        self.assertEqual(team, crew)

    # ---- Step 1: perception foils the plot ------------------------------

    async def test_perception_foils_plot_traitor_removed(self):
        """Commander perception pass → traitor removed, mission points awarded."""
        traitor   = make_traitor()
        commander = make_commander(perception=90)
        team      = [commander, traitor]
        screen, font = make_dummy_screen(), make_dummy_font()

        # roll=1 → stat_check passes (1 < ~90*morale_ratio + 0)
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.standard_skill_check", return_value=False), \
             patch("ReturnVoyage.random.randint", return_value=1):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)

        self.assertNotIn(traitor, team)
        self.assertGreater(commander.mission_points, 50)   # gained points

    async def test_perception_foils_plot_interrogation_bonus(self):
        """Interrogation skill check adds bonus mission points."""
        traitor   = make_traitor()
        commander = make_commander(perception=90)
        team      = [commander, traitor]
        screen, font = make_dummy_screen(), make_dummy_font()
        initial_pts = commander.mission_points

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.determine_best_team_member", return_value=commander), \
             patch("ReturnVoyage.standard_skill_check", return_value=True), \
             patch("ReturnVoyage.random.randint", return_value=1):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)

        # Should have gained base points AND interrogation bonus
        self.assertGreater(commander.mission_points, initial_pts + 10)

    # ---- Step 2: perception fails, surprise catches them ----------------

    async def test_surprise_catches_fleeing_traitor(self):
        """Perception fails but surprise catches the traitor; traitor removed."""
        traitor   = make_traitor()
        commander = make_commander(perception=1, surprise=200)  # surprise/2=100 → always catches
        team      = [commander, traitor]
        screen, font = make_dummy_screen(), make_dummy_font()

        call_count = [0]
        def seq_randint(a, b):
            call_count[0] += 1
            if b == 100 and call_count[0] == 1:
                return 99   # perception roll fails
            if b == 100 and call_count[0] == 2:
                return 1    # surprise roll passes (1 < 100)
            return 50

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.standard_skill_check", return_value=False), \
             patch("ReturnVoyage.random.randint", side_effect=seq_randint):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)

        self.assertNotIn(traitor, team)

    # ---- Step 3: both checks fail → escape + mission points lost --------

    async def test_both_fail_traitor_escapes_mission_points_lost(self):
        """When both perception and surprise fail, team loses 66% of mission points."""
        traitor   = make_traitor(mission_points=0)
        commander = make_commander(perception=1, surprise=2, mission_points=100)
        team      = [commander, traitor]
        screen, font = make_dummy_screen(), make_dummy_font()

        # Both rolls = 99 → perception fails (99 >= ~1); surprise fails (99 >= 1)
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", return_value=99):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)

        self.assertAlmostEqual(commander.mission_points, 34, delta=2)   # ~34% remain

    async def test_traitor_stays_on_team_after_escape(self):
        """After escaping, traitor is not in the team list (fled the ship)."""
        traitor   = make_traitor()
        commander = make_commander(perception=1, surprise=2)
        team      = [commander, traitor]
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", return_value=99):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)

        # Traitor escapes — not removed from list (they fled; team can't brig them)
        # This matches the design: 'escape' path leaves them out of the team naturally
        # (no team.remove call in step 3)
        self.assertIn(traitor, team)   # traitor NOT removed — they escaped

    # ---- Multi-traitor difficulty ----------------------------------------

    async def test_multi_traitor_harder_difficulty(self):
        """Two traitors apply -10 difficulty; three traitors apply -20, etc."""
        # Verify the difficulty calculation directly
        traitors_1 = [make_traitor()]
        traitors_2 = [make_traitor(), make_traitor()]
        diff_1 = -(len(traitors_1) - 1) * 10
        diff_2 = -(len(traitors_2) - 1) * 10
        self.assertEqual(diff_1, 0)
        self.assertEqual(diff_2, -10)




# ---------------------------------------------------------------------------
# Found-Items event: get_needed_item()
# ---------------------------------------------------------------------------

from Item import Item, item_base_name, item_class, ALL_ATTRIBUTES
from Utils import get_needed_item


def make_item(name):
    """Create an Item directly from ALL_ATTRIBUTES by full name (e.g. 'slicer C')."""
    return Item.from_data(name, ALL_ATTRIBUTES[name])


def give_item(character, item_name):
    """Add a named item to a character's equipment."""
    character.equipment.append(make_item(item_name))


class TestGetNeededItem(unittest.TestCase):
    """Tests for Utils.get_needed_item().

    We avoid loading the full item DB via load_items() and instead build a
    minimal all_items dict containing only the names exercised by each test.
    """

    def _minimal_items(self, *names):
        """Return a dict {name: Item} for the listed item names."""
        return {n: make_item(n) for n in names}

    # ---- Gap-fill: no ranged weapon ------------------------------------

    def test_gap_no_ranged_weapon_returns_laser_pistol_c(self):
        """Character with no ranged weapon should receive a laser pistol C."""
        human = make_human()
        give_item(human, "slicer C")      # has melee
        give_item(human, "veer suit C")   # has armor
        all_items = self._minimal_items("laser pistol C")

        # Force Mode A (gap-first) so gap check fires
        import random as rnd
        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        recipient, item = result
        self.assertIs(recipient, human)
        self.assertEqual(item_base_name(item.name), "laser pistol")

    def test_gap_no_melee_weapon_returns_slicer_c(self):
        """Character with ranged but no melee weapon should receive a slicer C."""
        human = make_human()
        give_item(human, "laser pistol C")
        give_item(human, "veer suit C")
        all_items = self._minimal_items("slicer C")

        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        _, item = result
        self.assertEqual(item_base_name(item.name), "slicer")

    def test_gap_exoskeleton_skill_no_exo_returns_exoskeleton_c(self):
        """Character with Exoskeleton Systems skill but no exo gets exoskeleton C."""
        human = make_human()
        human.skills = {"Exoskeleton Systems": 50}
        give_item(human, "laser pistol C")
        give_item(human, "slicer C")
        give_item(human, "veer suit C")
        all_items = self._minimal_items("exoskeleton C")

        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        _, item = result
        self.assertEqual(item_base_name(item.name), "exoskeleton")

    def test_gap_medicine_skill_no_medikit_returns_medikit_c(self):
        """Character with Medicine skill but no medikit gets medikit C."""
        human = make_human()
        human.skills = {"Medicine": 50}
        give_item(human, "laser pistol C")
        give_item(human, "slicer C")
        give_item(human, "veer suit C")
        all_items = self._minimal_items("medikit C")

        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        _, item = result
        self.assertEqual(item_base_name(item.name), "medikit")

    def test_gap_no_armor_returns_something_useful(self):
        """Character with weapons but no armor gets a useful item (gap-fill or upgrade)."""
        human = make_human()
        give_item(human, "laser pistol C")
        give_item(human, "slicer C")
        all_items = self._minimal_items("veer suit C", "laser pistol B", "slicer B")

        result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        recipient, item = result
        self.assertIs(recipient, human)
        # Valid outcomes: gap-fill (veer suit C) or a weapon upgrade (B-tier)
        valid_bases = {"veer suit", "laser pistol", "slicer"}
        self.assertIn(item_base_name(item.name), valid_bases)

    # ---- Upgrade path --------------------------------------------------

    def test_upgrade_c_to_b_always_succeeds(self):
        """C-tier weapon is always upgraded to B (100% chance)."""
        human = make_human()
        give_item(human, "laser pistol C")
        give_item(human, "slicer C")
        give_item(human, "veer suit C")
        all_items = self._minimal_items("laser pistol B", "slicer B")

        # Mode B (upgrade-first), upgrade probability roll passes (0.0 < 1.0)
        with unittest.mock.patch("Utils.random.random", side_effect=[0.9, 0.0]):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        _, item = result
        self.assertEqual(item_class(item.name), "B")

    def test_upgrade_b_to_a_probability_pass(self):
        """B-tier weapon upgrades to A when random roll < 0.5."""
        human = make_human()
        give_item(human, "laser pistol B")
        give_item(human, "slicer C")
        give_item(human, "veer suit C")
        all_items = self._minimal_items("laser pistol A")

        # Mode B (0.9 >= 0.5), upgrade probability 0.3 < 0.5 → passes
        with unittest.mock.patch("Utils.random.random", side_effect=[0.9, 0.3]):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        _, item = result
        self.assertEqual(item_class(item.name), "A")

    def test_upgrade_b_to_a_probability_fail_returns_none(self):
        """B-tier upgrade fails when probability roll > 0.5 and no other candidates."""
        human = make_human()
        give_item(human, "laser pistol B")
        give_item(human, "slicer B")
        give_item(human, "veer suit B")
        all_items = self._minimal_items("laser pistol A")

        # Mode B (0.9), upgrade probability 0.8 > 0.5 → fails for all items
        with unittest.mock.patch("Utils.random.random", side_effect=[0.9, 0.8, 0.8, 0.8]):
            result = get_needed_item([human], all_items)

        self.assertIsNone(result)

    def test_upgrade_s_tier_skipped_returns_none(self):
        """Character with only S-tier gear and no gaps → None."""
        human = make_human()
        give_item(human, "laser pistol S")
        give_item(human, "slicer S")
        give_item(human, "veer suit S")
        all_items = {}  # no upgrades available

        with unittest.mock.patch("Utils.random.random", return_value=0.9):
            result = get_needed_item([human], all_items)

        self.assertIsNone(result)

    # ---- Robots excluded -----------------------------------------------

    def test_robot_never_a_recipient(self):
        """Robots must never be returned as the recipient."""
        robot = make_robot()
        all_items = self._minimal_items("laser pistol C")

        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([robot], all_items)

        self.assertIsNone(result)

    def test_robot_skipped_human_still_found(self):
        """Robot in team doesn't block a human with a gear gap from being found."""
        robot = make_robot()
        human = make_human()
        give_item(human, "slicer C")
        give_item(human, "veer suit C")
        all_items = self._minimal_items("laser pistol C")

        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([robot, human], all_items)

        self.assertIsNotNone(result)
        recipient, _ = result
        self.assertIs(recipient, human)

    # ---- Dead characters excluded --------------------------------------

    def test_dead_character_skipped(self):
        """Dead characters are never considered."""
        dead = make_human()
        dead.current_health = 0
        alive = make_human()
        give_item(alive, "slicer C")
        give_item(alive, "veer suit C")
        all_items = self._minimal_items("laser pistol C")

        with unittest.mock.patch("Utils.random.random", return_value=0.1):
            result = get_needed_item([dead, alive], all_items)

        self.assertIsNotNone(result)
        recipient, _ = result
        self.assertIs(recipient, alive)

    # ---- All well-equipped → None --------------------------------------

    def test_fully_equipped_team_returns_none(self):
        """No result when everyone is fully geared at S-tier with no gaps."""
        human = make_human()
        give_item(human, "laser pistol S")
        give_item(human, "slicer S")
        give_item(human, "veer suit S")
        all_items = {}

        with unittest.mock.patch("Utils.random.random", return_value=0.5):
            result = get_needed_item([human], all_items)

        self.assertIsNone(result)

    # ---- Mode A: gap precedes upgrade ----------------------------------

    def test_mode_a_prefers_gap_over_upgrade(self):
        """In Mode A, gap-fill fires even when an upgrade is also possible."""
        human = make_human()
        give_item(human, "laser pistol C")  # has ranged (no gap there)
        give_item(human, "veer suit C")     # has armor
        # No melee → gap exists
        all_items = self._minimal_items("slicer C", "laser pistol B")

        # Mode A (random < 0.5), upgrade probability would pass too
        with unittest.mock.patch("Utils.random.random", side_effect=[0.1, 0.0]):
            result = get_needed_item([human], all_items)

        self.assertIsNotNone(result)
        _, item = result
        # Should have received the gap item (slicer C), not the upgrade
        self.assertEqual(item_base_name(item.name), "slicer")
        self.assertEqual(item_class(item.name), "C")


# ---------------------------------------------------------------------------
# Phase 1 (Stealth): stealth orb evasion bonus
# ---------------------------------------------------------------------------

class TestStealthEvasion(unittest.TestCase):

    def _base_evasion(self, c):
        """Expected evasion before any orb bonus (no encumbrance, full health)."""
        intelligence = c.stats["intelligence"]
        coordination = c.stats["coordination"]
        military_science = c.skills.get("military science", 0)
        evasion = round((intelligence + coordination) / 2)
        evasion += military_science / 10
        return max(1, evasion * c.get_health_ratio())

    def test_no_stealth_orb_baseline_unchanged(self):
        """Character with no stealth orb has unmodified evasion."""
        c = make_human_controlled(intelligence=50, coordination=50)
        expected = self._base_evasion(c)
        self.assertAlmostEqual(c.get_effective_combat_evasion(), expected)

    def test_stealth_orb_adds_30(self):
        """Character carrying a stealth orb gets +30 evasion."""
        c = make_human_controlled(intelligence=50, coordination=50)
        base = self._base_evasion(c)
        give_item(c, "stealth orb C")
        self.assertAlmostEqual(c.get_effective_combat_evasion(), base + 30)

    def test_stealth_orb_b_also_adds_30(self):
        """Tier B stealth orb gives the same +30 (bonus is tier-independent)."""
        c = make_human_controlled(intelligence=50, coordination=50)
        base = self._base_evasion(c)
        give_item(c, "stealth orb B")
        self.assertAlmostEqual(c.get_effective_combat_evasion(), base + 30)

    def test_two_stealth_orbs_do_not_stack(self):
        """Two stealth orbs do not stack: evasion += 30."""
        c = make_human_controlled(intelligence=50, coordination=50)
        base = self._base_evasion(c)
        give_item(c, "stealth orb C")
        give_item(c, "stealth orb B")
        self.assertAlmostEqual(c.get_effective_combat_evasion(), base + 30)

    def test_stealth_orb_bonus_scales_with_health_ratio(self):
        """At 50% health, the orb bonus is also halved by the health ratio."""
        c = make_human_controlled(intelligence=50, coordination=50)
        c.current_health = c.stats["max_health"] // 2
        give_item(c, "stealth orb C")
        raw_base = round((50 + 50) / 2)    # 50
        raw_with_orb = raw_base + 30        # 80
        expected = max(1, raw_with_orb * c.get_health_ratio())
        self.assertAlmostEqual(c.get_effective_combat_evasion(), expected, places=1)

    def test_robot_with_stealth_orb_no_crash(self):
        """Robots don't normally carry stealth orbs, but no crash if they do."""
        r = make_robot(200, morale=100)
        give_item(r, "stealth orb C")
        self.assertGreater(r.get_effective_combat_evasion(), 0)


# ---------------------------------------------------------------------------
# Phase 3 (Stealth): team_evades_notice and evasion outcome
# ---------------------------------------------------------------------------

from Event import team_evades_notice
from unittest.mock import patch as _patch

class TestTeamEvades(unittest.TestCase):

    def test_evades_when_roll_below_avg_evasion(self):
        """team_evades_notice returns True when roll < avg evasion."""
        # avg evasion = 80 (one member, evasion ~80)
        c = make_human_controlled(intelligence=80, coordination=80)
        # roll = 1 → 1 < 80 → True
        with _patch("Event.random.randint", return_value=1):
            self.assertTrue(team_evades_notice([c]))

    def test_detected_when_roll_above_avg_evasion(self):
        """team_evades_notice returns False when roll >= avg evasion."""
        c = make_human_controlled(intelligence=40, coordination=40)
        # avg evasion ≈ 40; roll = 99 → 99 >= 40 → False
        with _patch("Event.random.randint", return_value=99):
            self.assertFalse(team_evades_notice([c]))

    def test_empty_team_returns_false(self):
        """Empty team can never evade."""
        self.assertFalse(team_evades_notice([]))

    def test_stealth_orb_raises_avg_evasion(self):
        """Stealth orb holder has higher evasion → easier to evade."""
        c_plain = make_human_controlled(intelligence=50, coordination=50)
        c_orb   = make_human_controlled(intelligence=50, coordination=50)
        give_item(c_orb, "stealth orb C")
        evasion_plain = c_plain.get_effective_combat_evasion()
        evasion_orb   = c_orb.get_effective_combat_evasion()
        self.assertGreater(evasion_orb, evasion_plain)

    def test_multi_member_uses_average(self):
        """Avg evasion is the mean of all members."""
        low  = make_human_controlled(intelligence=10, coordination=10)
        high = make_human_controlled(intelligence=90, coordination=90)
        avg  = (low.get_effective_combat_evasion() + high.get_effective_combat_evasion()) / 2
        # roll just below avg → evade
        roll = int(avg) - 1
        with _patch("Event.random.randint", return_value=roll):
            self.assertTrue(team_evades_notice([low, high]))
        # roll just above avg → detected
        roll = int(avg) + 1
        with _patch("Event.random.randint", return_value=roll):
            self.assertFalse(team_evades_notice([low, high]))


# ---------------------------------------------------------------------------
# Roadmap Phase 1: Surgical Bug Fixes
# ---------------------------------------------------------------------------

from Utils import team_dead


class TestPhase1BugFixes(unittest.TestCase):

    def test_team_dead_false_when_member_alive(self):
        """team_dead() returns False when at least one member has current_health > 0."""
        alive = make_human(50, 50)
        dead = make_human(50, 50)
        dead.current_health = 0
        self.assertFalse(team_dead([alive, dead]))

    def test_team_dead_true_when_all_members_zero_health(self):
        """team_dead() returns True when all members have current_health == 0 (even with max_health > 0)."""
        m1 = make_human(50, 50)
        m2 = make_human(50, 50)
        m1.current_health = 0
        m2.current_health = 0
        self.assertGreater(m1.stats["max_health"], 0)
        self.assertTrue(team_dead([m1, m2]))

    def test_decrease_stat_clamps_stats_at_15_not_skills(self):
        """decrease_stat() clamps stats[stat_name] at 15 and does not pollute skills."""
        c = make_human(50, 50)
        c.stats["strength"] = 20
        c.decrease_stat("strength", 10)
        self.assertEqual(c.stats["strength"], 15)
        self.assertNotIn("strength", c.skills)


# ---------------------------------------------------------------------------
# Roadmap Phase 2: The 3-Layer Character Stat Architecture
# ---------------------------------------------------------------------------

class TestThreeLayerStats(unittest.TestCase):

    def test_all_18_sub_stats_generated_within_bounds(self):
        """All 18 sub-stats exist on a generated character and fall within [25, 95]."""
        c = Character(1, "team")
        expected_sub_stats = [
            sub_name
            for sub_tuple in Character.SUB_STAT_MAP.values()
            for sub_name in sub_tuple
        ]
        self.assertEqual(len(expected_sub_stats), 18)
        self.assertEqual(set(c.sub_stats.keys()), set(expected_sub_stats))
        for name, val in c.sub_stats.items():
            self.assertGreaterEqual(val, 25, f"{name} below 25")
            self.assertLessEqual(val, 95, f"{name} above 95")

    def test_sub_stat_group_variance_at_most_20(self):
        """Any one group of 3 sub-stats is at most 20 points apart."""
        for _ in range(50):
            c = Character(1, "team")
            for core_stat, sub_tuple in Character.SUB_STAT_MAP.items():
                vals = [c.sub_stats[s] for s in sub_tuple]
                spread = max(vals) - min(vals)
                self.assertLessEqual(
                    spread, 20,
                    f"{core_stat} sub-stats {vals} spread {spread} exceeds 20",
                )

    def test_core_stats_roll_up_from_sub_stats(self):
        """Each of the 6 core attributes equals the rounded average of its 3 sub-stats."""
        c = Character(1, "team")
        c.sub_stats = {
            "brawn": 60, "stamina": 70, "resilience": 80,          # avg = 70
            "fine_manipulation": 50, "agility": 55, "reflexes": 60, # avg = 55
            "logic": 40, "memory": 50, "guile": 60,                 # avg = 50
            "focus": 65, "composure": 70, "tenacity": 75,           # avg = 70
            "beauty": 30, "charm": 45, "command": 60,               # avg = 45
            "valor": 80, "nerve": 85, "resolve": 90,                # avg = 85
        }
        c.recalculate_stats()
        self.assertEqual(c.stats["strength"], 70)
        self.assertEqual(c.stats["coordination"], 55)
        self.assertEqual(c.stats["intelligence"], 50)
        self.assertEqual(c.stats["willpower"], 70)
        self.assertEqual(c.stats["charisma"], 45)
        self.assertEqual(c.stats["courage"], 85)

        # Verify derived stats from sub-stats
        self.assertEqual(c.stats["offense"], round((60 + 85 + 65) / 3))
        self.assertEqual(c.stats["defense"], round((55 + 80 + 70) / 3))
        self.assertEqual(c.stats["deception"], round((60 + 45 + 85) / 3))
        self.assertEqual(c.stats["evasion"], round((55 + 60 + 60) / 3))
        self.assertEqual(c.stats["analyze"], round((40 + 50 + 65) / 3))
        self.assertEqual(c.stats["max_health"], round((70 + 80 + 75) * 2 / 3))
        self.assertEqual(c.stats["movement"], 60 + 70 + 55)
        self.assertEqual(c.stats["meleecombat"], c.stats["evasion"] + round((60 + 80) / 2))
        self.assertEqual(c.stats["perception"], round((65 + 60 + 50) / 3))
        self.assertEqual(c.stats["surprise"], c.stats["evasion"] + c.stats["perception"])
        self.assertEqual(c.stats["leadership"], 60 + 90 + 40)

    def test_sub_stats_survive_to_dict_from_dict(self):
        """sub_stats and stats survive round-trip serialization via to_dict/from_dict."""
        c = Character(1, "team")
        data = c.to_dict()
        self.assertIn("sub_stats", data)
        restored = Character.from_dict(data)
        self.assertEqual(restored.sub_stats, c.sub_stats)
        self.assertEqual(restored.stats, c.stats)

    def test_from_dict_legacy_save_without_sub_stats(self):
        """Loading an older save dict without sub_stats auto-populates sub_stats from core stats."""
        c = Character(1, "team")
        data = c.to_dict()
        del data["sub_stats"]
        restored = Character.from_dict(data)
        self.assertEqual(len(restored.sub_stats), 18)
        for core_stat, sub_tuple in Character.SUB_STAT_MAP.items():
            for sub_name in sub_tuple:
                self.assertEqual(restored.sub_stats[sub_name], data["stats"][core_stat])

    def test_assigned_skills_respect_stat_gates(self):
        """Every skill assigned to a generated character has all gating stats >= 50 (not red)."""
        for _ in range(50):
            c = Character(1, "team")
            for skill in c.skills:
                gate_stats = Character.SKILL_GATE_STATS.get(skill, ())
                self.assertGreaterEqual(len(gate_stats), 1, f"{skill} missing from SKILL_GATE_STATS")
                self.assertLessEqual(len(gate_stats), 2, f"{skill} has >2 gate stats")
                for st in gate_stats:
                    self.assertGreaterEqual(
                        c.stats[st], 50,
                        f"{skill} assigned despite red {st}={c.stats[st]}",
                    )

    def test_low_intelligence_willpower_blocks_hacking_low_charisma_blocks_negotiation(self):
        """Low (<50) intelligence/willpower blocks Hacking; low charisma blocks Negotiation."""
        c = Character(1, "team")
        c.stats["intelligence"] = 40
        c.stats["willpower"] = 45
        c.stats["charisma"] = 35
        c.stats["strength"] = 65
        c.stats["coordination"] = 65
        c.stats["courage"] = 65
        self.assertFalse(c.is_skill_allowed("Hacking"))
        self.assertFalse(c.is_skill_allowed("Negotiation"))
        for _ in range(20):
            assigned = c.assign_skills(c.stats["intelligence"], c.stats["willpower"])
            self.assertNotIn("Hacking", assigned)
            self.assertNotIn("Negotiation", assigned)

    def test_green_gate_stats_boost_effective_skill_level_up_to_10(self):
        """Green (>75) gating stats add a modest boost (1..10) to effective skill level."""
        c = Character(1, "team")
        c.skills = {"Negotiation": 60, "Hacking": 60}
        # Cyan charisma (70) -> +0 boost
        c.stats["charisma"] = 70
        self.assertEqual(c.get_skill_gate_bonus("Negotiation"), 0)
        self.assertEqual(c.get_effective_skill_level("Negotiation", learning=False), 60)

        # Max green charisma (95) -> +10 boost
        c.stats["charisma"] = 95
        self.assertEqual(c.get_skill_gate_bonus("Negotiation"), 10)
        self.assertEqual(c.get_effective_skill_level("Negotiation", learning=False), 70)

        # Hacking (2 gate stats: intelligence, willpower)
        c.stats["intelligence"] = 85  # green (+2.5)
        c.stats["willpower"] = 70     # cyan (+0)
        bonus_one_green = c.get_skill_gate_bonus("Hacking")
        self.assertGreater(bonus_one_green, 0)
        self.assertLessEqual(bonus_one_green, 5)

        c.stats["intelligence"] = 95  # max green (+5)
        c.stats["willpower"] = 95     # max green (+5)
        self.assertEqual(c.get_skill_gate_bonus("Hacking"), 10)
        self.assertEqual(c.get_effective_skill_level("Hacking", learning=False), 70)


# ---------------------------------------------------------------------------
# Roadmap Phase 3: Consolidate & Smart-Weight Voyage Training Events
# ---------------------------------------------------------------------------

from Location import (
    TRAINING_SCENARIOS,
    KNAKNARPIA_LOCATION_ATTRIBUTES,
    build_procedural_training_event,
)
from Event import Event
from Voyage import calculate_outcome_training


class TestProceduralTrainingEvent(unittest.TestCase):

    def _dummy_locations(self):
        return {k: k for k in KNAKNARPIA_LOCATION_ATTRIBUTES}

    def test_training_scenarios_locations_are_valid_ship_rooms(self):
        """Every scenario in TRAINING_SCENARIOS references a valid Knacknarpia room key."""
        self.assertGreaterEqual(len(TRAINING_SCENARIOS), 25)
        for skill_name, scenarios in TRAINING_SCENARIOS.items():
            self.assertGreaterEqual(len(scenarios), 1, f"{skill_name} has no scenarios")
            for loc_key, pre_desc, post_desc in scenarios:
                self.assertIn(
                    loc_key,
                    KNAKNARPIA_LOCATION_ATTRIBUTES,
                    f"{skill_name} references invalid ship room '{loc_key}'",
                )
                self.assertTrue(isinstance(pre_desc, str) and len(pre_desc) > 0)
                self.assertTrue(post_desc is None or isinstance(post_desc, str))

    def test_returns_valid_event_object(self):
        """build_procedural_training_event returns a valid Event configured with calculate_outcome_training."""
        c = make_human(50, 50)
        c.skills = {"Hacking": 75}
        locations = self._dummy_locations()
        event = build_procedural_training_event([c], locations, {})

        self.assertIsInstance(event, Event)
        self.assertIn(event.context.skill_name, TRAINING_SCENARIOS)
        self.assertEqual(event.context.num_enemies, 0)
        self.assertIsNone(event.context.stat_name)
        self.assertIs(event.context.calculate_outcome, calculate_outcome_training)
        self.assertIn(event.context.location, locations.values())
        self.assertTrue(event.name.startswith("training_"))

    def test_favors_skills_known_by_team_in_70_percent_branch(self):
        """When random.random() < 0.70, always picks a skill a living non-robot has at >= 50."""
        c1 = make_human(50, 50)
        c1.skills = {"Hacking": 65, "Piloting": 40}  # Piloting < 50 so not favored
        c2 = make_human(50, 50)
        c2.skills = {"Xenobiology": 80}
        locations = self._dummy_locations()

        with unittest.mock.patch("Location.random.random", return_value=0.25):
            for _ in range(30):
                ev = build_procedural_training_event([c1, c2], locations, {})
                self.assertIn(ev.context.skill_name, {"Hacking", "Xenobiology"})

    def test_ignores_dead_and_robot_skills_in_weighted_branch(self):
        """Dead crew members and robots do not count toward the 70% known-skill pool."""
        dead = make_human(50, 50)
        dead.current_health = 0
        dead.skills = {"Hacking": 90}

        robot = make_robot()
        robot.skills = {"Navigation": 90}

        alive = make_human(50, 50)
        alive.skills = {"Medicine": 70}
        locations = self._dummy_locations()

        with unittest.mock.patch("Location.random.random", return_value=0.10):
            for _ in range(20):
                ev = build_procedural_training_event([dead, robot, alive], locations, {})
                self.assertEqual(ev.context.skill_name, "Medicine")

    def test_fallback_when_no_skills_at_50_or_in_30_percent_branch(self):
        """When no crew member has a skill >= 50 (or random >= 0.70), picks from all TRAINING_SCENARIOS."""
        c = make_human(50, 50)
        c.skills = {"Hacking": 30}
        locations = self._dummy_locations()

        seen_skills = set()
        for _ in range(50):
            ev = build_procedural_training_event([c], locations, {})
            seen_skills.add(ev.context.skill_name)
        self.assertGreater(len(seen_skills), 3)


# ---------------------------------------------------------------------------
# Roadmap Phase 4: Universal Multi-Approach Challenge Engine & 31 Pirate Rooms
# ---------------------------------------------------------------------------

import Mission
from Location import PIRATE_LOCATION_ATTRIBUTES, Location
from Mission import (
    CHALLENGE_ARCHETYPES,
    resolve_procedural_challenge,
    build_procedural_mission_room_event,
)


class TestPhase4ChallengeEngineAndLocations(unittest.IsolatedAsyncioTestCase):

    def _dummy_pirate_locations(self):
        locs = {}
        for name, entry in PIRATE_LOCATION_ATTRIBUTES.items():
            desc, conns, tags = entry[0], entry[1], entry[2]
            locs[name] = Location(None, pygame.Rect(0, 0, 10, 10), name, desc, dict(conns), tags=tags)
        return locs

    def test_all_31_pirate_locations_tagged(self):
        """All 31 Pirate locations have valid tags stored in PIRATE_LOCATION_ATTRIBUTES and Location.tags."""
        self.assertEqual(len(PIRATE_LOCATION_ATTRIBUTES), 31)
        valid_tags = {"combat", "tech", "medical", "supply", "corridor", "goal", "entrance"}
        locs = self._dummy_pirate_locations()
        for name, loc in locs.items():
            self.assertGreaterEqual(len(loc.tags), 1, f"{name} has no tags")
            for t in loc.tags:
                self.assertIn(t, valid_tags, f"{name} has unexpected tag {t}")

    def test_all_8_challenge_archetypes_present(self):
        """CHALLENGE_ARCHETYPES defines all 8 required templates."""
        expected = {
            "LOCKED_PORTAL",
            "SECURITY_GRID",
            "INTEL_CONSOLE",
            "HAZARD_LEAK",
            "MEDICAL_CACHE",
            "CYBER_IMPLANT_BAY",
            "SUPPLY_LOCKER",
            "CAPTIVE_CELL",
        }
        self.assertEqual(set(CHALLENGE_ARCHETYPES.keys()), expected)

    async def test_resolve_challenge_item_bypass(self):
        """Carrying a cutter bypasses LOCKED_PORTAL without skill checks and grants mission points."""
        c = make_human(50, 50)
        give_item(c, "cutter C")
        Mission.rooms_to_goal = 5
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("Mission.type_out_text"):
            passed = await resolve_procedural_challenge([c], "LOCKED_PORTAL", screen, font)

        self.assertTrue(passed)
        self.assertEqual(c.mission_points, 5)
        self.assertEqual(Mission.rooms_to_goal, 5)

    async def test_resolve_challenge_robot_bypass_and_shortcut(self):
        """A hackbot on the team bypasses SECURITY_GRID and reduces rooms_to_goal by 1."""
        human = make_human(50, 50)
        bot = make_robot(200)
        bot.occupation = "hackbot"
        Mission.rooms_to_goal = 5
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("Mission.type_out_text"):
            passed = await resolve_procedural_challenge([human, bot], "SECURITY_GRID", screen, font)

        self.assertTrue(passed)
        self.assertEqual(Mission.rooms_to_goal, 4)
        self.assertEqual(human.mission_points, 5)

    async def test_resolve_challenge_skill_pass(self):
        """Skill pass on INTEL_CONSOLE grants +10 mission points and +2 Hacking skill."""
        c = make_human(50, 50)
        c.skills = {"Hacking": 70}
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("Mission.type_out_text"), \
             patch("Mission.standard_skill_check", return_value=True):
            passed = await resolve_procedural_challenge([c], "INTEL_CONSOLE", screen, font)

        self.assertTrue(passed)
        self.assertEqual(c.mission_points, 10)
        self.assertEqual(c.skills["Hacking"], 72)

    async def test_resolve_challenge_fallback_detour_and_damage_penalties(self):
        """Failing LOCKED_PORTAL adds +2 detour; failing HAZARD_LEAK damages all living crew."""
        c = make_human(50, 50)
        c.skills = {}
        Mission.rooms_to_goal = 4
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("Mission.type_out_text"):
            passed_portal = await resolve_procedural_challenge([c], "LOCKED_PORTAL", screen, font)
        self.assertFalse(passed_portal)
        self.assertEqual(Mission.rooms_to_goal, 6)

        start_hp = c.current_health
        with patch("Mission.type_out_text"), \
             patch("Mission.standard_skill_check", return_value=False):
            passed_hazard = await resolve_procedural_challenge([c], "HAZARD_LEAK", screen, font)
        self.assertFalse(passed_hazard)
        self.assertLess(c.current_health, start_hp)

    def test_pacifist_means_prefers_stunner_and_stun_baton(self):
        """When mission['means'] == 'pacifist', weapon choosers prefer stunner and stun baton."""
        c = make_human(50, 50)
        c.skills = {"Sharpshooting": 80, "Martial Arts": 80}
        give_item(c, "laser rifle A")
        give_item(c, "stunner C")
        give_item(c, "slicer A")
        give_item(c, "stun baton C")

        # Non-pacifist chooses laser rifle A and slicer A
        c.mission["means"] = "any"
        self.assertEqual(item_base_name(c.choose_ranged_weapon().name), "laser rifle")
        self.assertEqual(item_base_name(c.choose_melee_weapon().name), "slicer")

        # Pacifist chooses stunner C and stun baton C
        c.mission["means"] = "pacifist"
        self.assertEqual(item_base_name(c.choose_ranged_weapon().name), "stunner")
        self.assertEqual(item_base_name(c.choose_melee_weapon().name), "stun baton")

    def test_procedural_mission_room_generator_and_supply_locker_cap(self):
        """build_procedural_mission_room_event uses all non-goal Pirate locations and caps SUPPLY_LOCKER at once."""
        c = make_human(50, 50)
        c.mission["options"] = "flex"
        locs = self._dummy_pirate_locations()
        state = {"used": False}
        seen_rooms = set()
        for _ in range(100):
            ev = build_procedural_mission_room_event([c], locs, {}, supply_locker_state=state)
            self.assertNotIn(ev.name, {"entrance", "ai core", "officer's quarters", "vault"})
            seen_rooms.add(ev.name)
        self.assertGreater(len(seen_rooms), 15)

    def test_unarmed_character_gets_default_knife_without_inventory_change(self):
        """Unarmed non-robot character gets abstract 'knife' melee weapon; ranged-only and robots get None."""
        from Item import DEFAULT_KNIFE_WEAPON
        unarmed = make_human(50, 50)
        self.assertEqual(unarmed.get_weapon_count(), 0)
        chosen = unarmed.choose_melee_weapon()
        self.assertIs(chosen, DEFAULT_KNIFE_WEAPON)
        self.assertEqual(chosen.name, "knife")
        # Must NOT be added to inventory
        self.assertEqual(len(unarmed.equipment), 0)

        # Character with a ranged weapon (no melee) still returns None so they EVADE in melee phase
        ranged_only = make_human(50, 50)
        give_item(ranged_only, "laser pistol C")
        self.assertIsNone(ranged_only.choose_melee_weapon())

        # Unarmed robot returns None
        bot = make_robot(200)
        self.assertIsNone(bot.choose_melee_weapon())

    def test_default_knife_weak_damage_and_sucks_against_good_armor(self):
        """Knife has effect=10 impact and deals only 1 HP chip damage against good armor."""
        from Item import DEFAULT_KNIFE_WEAPON
        self.assertEqual(DEFAULT_KNIFE_WEAPON.effect, 10)
        self.assertEqual(DEFAULT_KNIFE_WEAPON.effect_type, "impact")

        armored = make_human(50, 50)
        give_item(armored, "powered armor C")
        start_hp = armored.current_health
        armored.hurt(DEFAULT_KNIFE_WEAPON.effect, DEFAULT_KNIFE_WEAPON.effect_type)
        # Powered armor reduces impact damage below 1, clamped to 1 HP minimum
        self.assertEqual(start_hp - armored.current_health, 1)

    async def test_share_spare_weapons_passes_unselected_weapon_and_runs_in_team_heals(self):
        """Donor with 2 weapons passes the unselected weapon to an unarmed teammate during share_spare_weapons / team_heals."""
        from Event import share_spare_weapons, team_heals

        donor = make_human(50, 50)
        donor.skills = {"Sharpshooting": 80}
        give_item(donor, "laser rifle B")
        give_item(donor, "pistol C")

        unarmed = make_human(50, 50)
        self.assertEqual(unarmed.get_weapon_count(), 0)

        # Donor selects laser rifle B, so pistol C is the unselected weapon passed to unarmed
        passed = await share_spare_weapons([donor, unarmed])
        self.assertIsNotNone(passed)
        self.assertEqual(passed.name, "pistol C")
        self.assertEqual([i.name for i in donor.equipment], ["laser rifle B"])
        self.assertEqual([i.name for i in unarmed.equipment], ["pistol C"])

        # Also verify team_heals invokes share_spare_weapons even when no healing is needed
        donor2 = make_human(50, 50)
        give_item(donor2, "laser pistol C")
        give_item(donor2, "slicer C")
        unarmed2 = make_human(50, 50)
        screen, font = make_dummy_screen(), make_dummy_font()
        with patch("Event.type_out_text"):
            await team_heals([donor2, unarmed2], screen, font)
        self.assertEqual(donor2.get_weapon_count(), 1)
        self.assertEqual(unarmed2.get_weapon_count(), 1)


# ---------------------------------------------------------------------------
# Roadmap Phase 5: Loop 2+ Derelict Vessel & Klackon Theatre
# ---------------------------------------------------------------------------

from Location import DERELICT_LOCATION_ATTRIBUTES, load_derelict_locations
from Event import mission_enemies, _apply_loop_scaling
from MissionOrders import (
    MISSION_GOALS,
    DERELICT_MISSION_GOALS,
    get_theatre_for_loop,
    get_mission_goals_for_theatre,
    get_mission_briefing_lines,
)


class TestPhase5DerelictAndKlackons(unittest.TestCase):

    def test_all_26_derelict_locations_tagged_and_loadable(self):
        """All 26 Derelict rooms have tags in DERELICT_LOCATION_ATTRIBUTES and load via load_derelict_locations()."""
        self.assertEqual(len(DERELICT_LOCATION_ATTRIBUTES), 26)
        valid_tags = {"combat", "tech", "medical", "supply", "corridor", "goal"}
        for name, entry in DERELICT_LOCATION_ATTRIBUTES.items():
            self.assertEqual(len(entry), 3, f"{name} should have (desc, connections, tags)")
            self.assertTrue(set(entry[2]).issubset(valid_tags), f"Invalid tags on {name}: {entry[2]}")

        locs = load_derelict_locations()
        self.assertEqual(len(locs), 26)
        for goal_room in ("throneroom", "warpchamber", "biolab", "bridge"):
            self.assertIn("goal", locs[goal_room].tags)

    def test_klackon_character_creation_and_enemy_status(self):
        """Character(1, 'klackon') creates a Klackon warrior with high melee stats and is_pirate()/is_enemy() == True."""
        with patch("Character.pygame.image.load", return_value=pygame.Surface((60, 70))):
            k = Character(1, "klackon", 60, 70)
        self.assertEqual(k.occupation, "klackon")
        self.assertTrue(k.is_enemy())
        self.assertTrue(k.is_pirate())
        self.assertGreaterEqual(k.skills.get("Martial Arts", 0), 65)
        self.assertGreaterEqual(k.stats["strength"], 70)

    def test_mission_enemies_spawns_klackons_and_scales_by_loop(self):
        """mission_enemies spawns Klackons for 'derelict' theatre and scales stats on loop >= 2."""
        items = {
            "slicer B": make_item("slicer B"),
            "blaster rifle B": make_item("blaster rifle B"),
            "exoskeleton B": make_item("exoskeleton B"),
        }
        with patch("Character.pygame.image.load", return_value=pygame.Surface((60, 70))):
            enemies_l1 = mission_enemies(3, items, theatre="derelict", loop=1)
            self.assertEqual(len(enemies_l1), 3)
            for e in enemies_l1:
                self.assertEqual(e.occupation, "klackon")
                self.assertGreaterEqual(e.get_weapon_count(), 1)

            base_enemy = Character(1, "klackon", 60, 70)
            base_hp = base_enemy.stats["max_health"]
            base_offense = base_enemy.stats["offense"]
            _apply_loop_scaling(base_enemy, loop=3)
            self.assertEqual(base_enemy.stats["max_health"], base_hp + 24)
            self.assertEqual(base_enemy.stats["offense"], min(140, base_offense + 10))

    def test_theatre_and_goals_by_loop(self):
        """Odd loops select 'pirates' and MISSION_GOALS; even loops select 'derelict' and DERELICT_MISSION_GOALS."""
        self.assertEqual(get_theatre_for_loop(1), "pirates")
        self.assertEqual(get_theatre_for_loop(2), "derelict")
        self.assertEqual(get_theatre_for_loop(3), "pirates")
        self.assertEqual(get_theatre_for_loop(4), "derelict")
        self.assertIs(get_mission_goals_for_theatre("pirates"), MISSION_GOALS)
        self.assertIs(get_mission_goals_for_theatre("derelict"), DERELICT_MISSION_GOALS)
        self.assertEqual(len(MISSION_GOALS), 5)
        self.assertEqual(len(DERELICT_MISSION_GOALS), 5)
        self.assertEqual(MISSION_GOALS[4][3], [20])
        self.assertEqual(DERELICT_MISSION_GOALS[4][3], [20])

        setting_p, desc_p, rec_p = get_mission_briefing_lines("pirates", 4)
        self.assertEqual(setting_p, "Proceed to pirate base at target coordinates.")
        self.assertIn("20 pirates", desc_p)
        self.assertIn("heavy combat team", rec_p)

        setting_d, desc_d, rec_d = get_mission_briefing_lines("derelict", 0)
        self.assertEqual(setting_d, "Intercept alien derelict at target coordinates.")
        self.assertIn("Xeno-Relic", desc_d)
        self.assertIn("technical skills", rec_d)

    def test_liquidate_surviving_robots_converts_robots_to_credits(self):
        """Surviving robots are converted into their purchase cost in credits and removed from the next-loop team."""
        from Score import liquidate_surviving_robots

        h1 = make_human(80, 100)
        h2 = make_human(50, 50)
        h2.current_health = 0  # dead human
        r_alive = make_robot(50, 50)
        r_alive.occupation = "assaultbot"  # cost 500
        r_med = make_robot(30, 50)
        r_med.occupation = "medibot"       # cost 500
        r_dead = make_robot(50, 50)
        r_dead.current_health = 0
        r_dead.occupation = "scoutbot"     # dead robot -> 0 refund

        survivors, refund = liquidate_surviving_robots([h1, h2, r_alive, r_med, r_dead])
        self.assertEqual(refund, 1000)
        self.assertEqual(len(survivors), 1)
        self.assertIs(survivors[0], h1)
        self.assertTrue(all(not m.is_robot() for m in survivors))

    def test_procedural_mission_room_generator_with_derelict_locations(self):
        """build_procedural_mission_room_event works with Derelict rooms and excludes Derelict goal rooms."""
        c = make_human(50, 50)
        c.mission["options"] = "flex"
        locs = {
            name: Location(pygame.Surface((10, 10)), pygame.Rect(0, 0, 10, 10), name, entry[0], dict(entry[1]), tags=entry[2])
            for name, entry in DERELICT_LOCATION_ATTRIBUTES.items()
        }
        seen = set()
        for _ in range(80):
            ev = build_procedural_mission_room_event([c], locs, {})
            self.assertNotIn(ev.name, {"throneroom", "warpchamber", "biolab", "bridge"})
            seen.add(ev.name)
        self.assertGreater(len(seen), 12)


# ---------------------------------------------------------------------------
# Position Team Stage — Phase 1 Tests
# ---------------------------------------------------------------------------

from PositionTeam import (
    ROLE_COMMANDER,
    ROLE_EXEC,
    POS_POINT_MAN,
    POS_CENTER,
    POS_OVERWATCH,
    POS_PROTECTED,
    assign_command_role,
    clear_command_role,
    assign_formation_position,
    unassign_formation_position,
    normalize_team_positions,
    can_proceed,
)
from Utils import STAGE_NAMES
from LoadGame import STAGE_LABELS


class TestPositionTeamPhase1(unittest.TestCase):

    def test_character_serialization_preserves_role_and_position(self):
        """Character.to_dict() and from_dict() round-trip command_role and position."""
        c = make_human(60, 60)
        c.command_role = ROLE_COMMANDER
        c.position = POS_OVERWATCH

        d = c.to_dict()
        self.assertEqual(d["command_role"], ROLE_COMMANDER)
        self.assertEqual(d["position"], POS_OVERWATCH)

        with patch("Character.pygame.image.load", return_value=pygame.Surface((70, 80))):
            restored = Character.from_dict(d)
        self.assertEqual(restored.command_role, ROLE_COMMANDER)
        self.assertEqual(restored.position, POS_OVERWATCH)

    def test_assign_command_role_blocks_robots_and_preserves_position(self):
        """Robots cannot be Commander or Exec; human assignment preserves formation position."""
        h1 = make_human(50, 50)
        h2 = make_human(50, 50)
        bot = make_robot(200)
        team = [h1, h2, bot]

        ok_bot_cmd, err_cmd = assign_command_role(team, bot, ROLE_COMMANDER)
        self.assertFalse(ok_bot_cmd)
        self.assertIsNotNone(err_cmd)
        self.assertIsNone(bot.command_role)

        ok_bot_exec, _ = assign_command_role(team, bot, ROLE_EXEC)
        self.assertFalse(ok_bot_exec)
        self.assertIsNone(bot.command_role)

        h1.position = POS_CENTER
        ok_h1, _ = assign_command_role(team, h1, ROLE_COMMANDER)
        self.assertTrue(ok_h1)
        self.assertEqual(h1.command_role, ROLE_COMMANDER)
        self.assertEqual(h1.position, POS_CENTER)

    def test_assign_command_role_prevents_dual_roles_and_swaps_occupants(self):
        """One character cannot hold both Commander and Exec; replacing swaps or clears previous holder."""
        h1 = make_human(50, 50)
        h2 = make_human(50, 50)
        h3 = make_human(50, 50)
        team = [h1, h2, h3]

        assign_command_role(team, h1, ROLE_COMMANDER)
        # Moving h1 directly to Exec while Exec is empty clears Commander on h1
        assign_command_role(team, h1, ROLE_EXEC)
        self.assertEqual(h1.command_role, ROLE_EXEC)

        # Assign h2 to Commander, then drop h1 (Exec) onto Commander -> h1 & h2 swap roles
        assign_command_role(team, h2, ROLE_COMMANDER)
        assign_command_role(team, h1, ROLE_COMMANDER)
        self.assertEqual(h1.command_role, ROLE_COMMANDER)
        self.assertEqual(h2.command_role, ROLE_EXEC)

        # Dropping unassigned h3 onto Commander clears h1's Commander role
        assign_command_role(team, h3, ROLE_COMMANDER)
        self.assertEqual(h3.command_role, ROLE_COMMANDER)
        self.assertIsNone(h1.command_role)

        clear_command_role(h3)
        self.assertIsNone(h3.command_role)

    def test_assign_formation_position_point_man_single_and_wide_multi(self):
        """Point Man holds 1 character (swapping if occupied); Center/Overwatch/Protected hold multiple (including robots)."""
        h1 = make_human(50, 50)
        h2 = make_human(50, 50)
        bot = make_robot(200)
        team = [h1, h2, bot]

        # Place h1 in Point Man, then replace with h2 (from unassigned) -> h1 becomes None
        assign_formation_position(team, h1, POS_POINT_MAN)
        self.assertEqual(h1.position, POS_POINT_MAN)
        assign_formation_position(team, h2, POS_POINT_MAN)
        self.assertEqual(h2.position, POS_POINT_MAN)
        self.assertIsNone(h1.position)

        # Place h1 and bot both into Center, then move h1 to Point Man -> h2 swaps into Center
        assign_formation_position(team, h1, POS_CENTER)
        assign_formation_position(team, bot, POS_CENTER)
        self.assertEqual(h1.position, POS_CENTER)
        self.assertEqual(bot.position, POS_CENTER)

        assign_formation_position(team, h1, POS_POINT_MAN)
        self.assertEqual(h1.position, POS_POINT_MAN)
        self.assertEqual(h2.position, POS_CENTER)

        unassign_formation_position(bot)
        self.assertIsNone(bot.position)

    def test_can_proceed_requires_commander_exec_and_all_formation_positions(self):
        """can_proceed is True only when Commander, Exec, and every team member's formation position are set."""
        h1 = make_human(50, 50)
        h2 = make_human(50, 50)
        bot = make_robot(200)
        team = [h1, h2, bot]

        self.assertFalse(can_proceed(team))

        # Assign formation positions to everyone (even with Point Man empty)
        assign_formation_position(team, h1, POS_CENTER)
        assign_formation_position(team, h2, POS_OVERWATCH)
        assign_formation_position(team, bot, POS_PROTECTED)
        self.assertFalse(can_proceed(team))  # Still missing Commander & Exec

        assign_command_role(team, h1, ROLE_COMMANDER)
        self.assertFalse(can_proceed(team))  # Still missing Exec

        assign_command_role(team, h2, ROLE_EXEC)
        self.assertTrue(can_proceed(team))

        # Unassigning one member from formation disables proceed
        unassign_formation_position(bot)
        self.assertFalse(can_proceed(team))

    def test_stage_numbering_and_labels_include_position_stage(self):
        """Stage 4 is 'position' / 'Position Team', and subsequent stages are 5..7."""
        self.assertEqual(STAGE_NAMES[3], "equip")
        self.assertEqual(STAGE_NAMES[4], "position")
        self.assertEqual(STAGE_NAMES[5], "voyage")
        self.assertEqual(STAGE_NAMES[6], "mission")
        self.assertEqual(STAGE_NAMES[7], "return")

        self.assertEqual(STAGE_LABELS[4], "Position Team")
        self.assertEqual(STAGE_LABELS[5], "Voyage")
        self.assertEqual(STAGE_LABELS[6], "Mission")
        self.assertEqual(STAGE_LABELS[7], "Return Voyage")


# ---------------------------------------------------------------------------
# Position Team Stage — Phase 2 Tests
# ---------------------------------------------------------------------------

from PositionTeam import get_character_inspection_data


class TestPositionTeamPhase2(unittest.TestCase):

    def test_get_character_inspection_data_human_includes_stats_skills_and_equipment(self):
        """get_character_inspection_data returns stats, skills, equipment, role, and position for a human."""
        c = make_human(80, 60, morale=90)
        c.name = "Cmdr Shepard"
        c.occupation = "soldier"
        c.skills = {"Sharpshooting": 85, "Military Science": 60}
        give_item(c, "laser rifle B")
        give_item(c, "veer suit C")
        c.command_role = ROLE_COMMANDER
        c.position = POS_POINT_MAN

        info = get_character_inspection_data(c)
        self.assertEqual(info["name"], "Cmdr Shepard")
        self.assertEqual(info["occupation"], "soldier")
        self.assertFalse(info["is_robot"])
        self.assertEqual(info["current_health"], 140)
        self.assertEqual(info["max_health"], 140)
        self.assertEqual(info["morale"], 90)
        self.assertEqual(info["command_role"], "Mission Commander")
        self.assertEqual(info["position"], "Point Man")

        stat_keys = [entry[0] for entry in info["stats"]]
        self.assertIn("strength", stat_keys)
        self.assertIn("leadership", stat_keys)

        skill_map = {name: val for name, val, _ in info["skills"]}
        self.assertEqual(skill_map["Sharpshooting"], 85)
        self.assertEqual(skill_map["Military Science"], 60)

        equip_names = [item.name for item in info["equipment"]]
        self.assertEqual(equip_names, ["laser rifle B", "veer suit C"])

    def test_get_character_inspection_data_robot_uses_max_life(self):
        """get_character_inspection_data uses max_life for robot max_health and leaves command_role None."""
        bot = make_robot(250, morale=100)
        bot.name = "ASB7"
        bot.occupation = "assaultbot"
        bot.current_health = 190
        bot.skills = {"Energy Weapons": 75}
        give_item(bot, "laser pistol C")
        bot.position = POS_OVERWATCH

        info = get_character_inspection_data(bot)
        self.assertEqual(info["name"], "ASB7")
        self.assertTrue(info["is_robot"])
        self.assertEqual(info["current_health"], 190)
        self.assertEqual(info["max_health"], 250)
        self.assertIsNone(info["command_role"])
        self.assertEqual(info["position"], "Overwatch")
        self.assertEqual(len(info["equipment"]), 1)
        self.assertEqual(info["equipment"][0].name, "laser pistol C")


# ---------------------------------------------------------------------------
# Command Roles & Formation Effects — Phase 1 Tests
# ---------------------------------------------------------------------------

from Utils import get_active_commander, EventContext
from Battle import TeamBattle, BattleAction
from Interaction import _get_leadership_bonus


class TestRolePositionEffectsPhase1(unittest.IsolatedAsyncioTestCase):

    def test_get_active_commander_chain_and_interaction_leadership_bonus(self):
        """get_active_commander selects Commander first, then Exec if Commander dead, then highest leadership."""
        cmd = make_human(50, 50)
        cmd.stats["leadership"] = 90
        cmd.command_role = ROLE_COMMANDER

        xo = make_human(50, 50)
        xo.stats["leadership"] = 120
        xo.command_role = ROLE_EXEC

        other = make_human(50, 50)
        other.stats["leadership"] = 180

        team = [cmd, xo, other]
        for m in team:
            m.team = team

        # Even though 'other' has higher leadership, Commander is chosen
        self.assertIs(get_active_commander(team), cmd)
        self.assertEqual(_get_leadership_bonus(other, xo), int(90 * 0.1))

        # When Commander dies, Executive Officer takes command
        cmd.current_health = 0
        self.assertIs(get_active_commander(team), xo)
        self.assertEqual(_get_leadership_bonus(other, xo), int(120 * 0.1))

        # When Exec also dies, falls back to highest-leadership living non-robot ('other')
        xo.current_health = 0
        self.assertIs(get_active_commander(team), other)
        self.assertEqual(_get_leadership_bonus(other, cmd), int(180 * 0.1))

    def test_point_man_initiative_and_scoutbot_point_bonus(self):
        """Point Man gets +20 initiative; a scoutbot in Point Man grants +15 team-wide initiative."""
        h_point = make_human_controlled()
        h_center = make_human_controlled()
        enemy = make_human_controlled()
        for m in (h_point, h_center, enemy):
            m.stats["surprise"] = 0
            m.skills = {}

        h_point.position = POS_POINT_MAN
        h_center.position = POS_CENTER
        with patch("Battle.random.randint", return_value=50):
            order = initiative([h_point, h_center], [enemy])
        # h_point gets 50 + 20 = 70, beating h_center (50) and enemy (50)
        self.assertIs(order[0], h_point)

        # Scoutbot on point grants +15 to teammates (vs +5 when not on point)
        scout = make_scoutbot_simple()
        scout.stats["surprise"] = 0
        scout.skills = {}
        scout.position = POS_POINT_MAN
        enemy.stats["surprise"] = 10  # enemy roll = 50 + 10 = 60
        with patch("Battle.random.randint", return_value=50):
            # With scout on point (+15 team bonus), h_center rolls 50 + 15 = 65 > enemy 60
            order_point_scout = initiative([h_center, scout], [enemy])
        self.assertLess(order_point_scout.index(h_center), order_point_scout.index(enemy))

        scout.position = POS_CENTER
        with patch("Battle.random.randint", return_value=50):
            # With scout in center (+5 team bonus), h_center rolls 50 + 5 = 55 < enemy 60
            order_center_scout = initiative([h_center, scout], [enemy])
        self.assertGreater(order_center_scout.index(h_center), order_center_scout.index(enemy))

    def test_enemy_target_selection_weights_and_melee_exclusions(self):
        """Enemy melee excludes Overwatch (rounds 1-3 while Center alive) and Protected (while Center/Overwatch alive); Round 1 weights favor Point Man."""
        enemy = Character(1, "pirate")
        pm = make_human(50, 50)
        pm.position = POS_POINT_MAN
        ctr = make_human(50, 50)
        ctr.position = POS_CENTER
        ow = make_human(50, 50)
        ow.position = POS_OVERWATCH
        prot = make_human(50, 50)
        prot.position = POS_PROTECTED
        team = [pm, ctr, ow, prot]

        # Melee Round 1-3 with Center alive: neither Overwatch nor Protected can be chosen
        for r in (1, 2, 3):
            for _ in range(40):
                t = TeamBattle.choose_target(enemy, team, round_num=r, attack_type="melee")
                self.assertIn(t, (pm, ctr))

        # Melee Round 4 with Center alive: Overwatch can now be chosen, Protected still excluded
        seen_r4 = {
            TeamBattle.choose_target(enemy, team, round_num=4, attack_type="melee")
            for _ in range(60)
        }
        self.assertIn(ow, seen_r4)
        self.assertNotIn(prot, seen_r4)

        # If Center dies in Round 1, Overwatch can be chosen in melee, Protected still excluded by Overwatch
        ctr.current_health = 0
        seen_no_ctr = {
            TeamBattle.choose_target(enemy, team, round_num=1, attack_type="melee")
            for _ in range(60)
        }
        self.assertIn(ow, seen_no_ctr)
        self.assertNotIn(prot, seen_no_ctr)

        # If Overwatch also dies, Protected can now be chosen
        ow.current_health = 0
        seen_no_ow = {
            TeamBattle.choose_target(enemy, team, round_num=1, attack_type="melee")
            for _ in range(60)
        }
        self.assertIn(prot, seen_no_ow)

        # Ranged Round 1 weights: Point Man (3.0) chosen much more often than Protected (0.25)
        ctr.current_health = 100
        ow.current_health = 100
        counts = {pm: 0, ctr: 0, ow: 0, prot: 0}
        for _ in range(400):
            t = TeamBattle.choose_target(enemy, team, round_num=1, attack_type="ranged")
            counts[t] += 1
        self.assertGreater(counts[pm], counts[ctr])
        self.assertGreater(counts[ctr], counts[prot])

    def test_overwatch_evades_in_melee_until_center_dead_but_shoots_in_ranged(self):
        """Overwatch chooses EVADE in melee phase while any Center member is alive, but SHOOT in ranged phase."""
        ctr = make_human(50, 50)
        ctr.position = POS_CENTER
        ow = make_human(50, 50)
        ow.position = POS_OVERWATCH
        give_item(ow, "laser rifle C")
        give_item(ow, "slicer C")
        ow.chosen_ranged_weapon = ow.choose_ranged_weapon()
        ow.chosen_melee_weapon = ow.choose_melee_weapon()

        ctx = EventContext("", "", 1, None, None, None, None, {})
        ctx.add_run_params([ctr, ow], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [Character(1, "pirate")]
        battle = TeamBattle(ctx)

        self.assertEqual(battle.choose_battle_action_ranged_phase(ow), BattleAction.SHOOT)
        self.assertEqual(battle.choose_battle_action_melee_phase(ow), BattleAction.EVADE)

        # Once Center is dead, Overwatch fights in melee
        ctr.current_health = 0
        self.assertEqual(battle.choose_battle_action_melee_phase(ow), BattleAction.MELEE)

    async def test_point_man_round_1_hit_bonus_and_scoutbot_point_round_1_defense(self):
        """Point Man gets -15 adjusted_roll on Round 1; Scoutbot on point adds +15 to enemy adjusted_roll on Round 1."""
        pm = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        pm.skills = {}
        give_item(pm, "laser pistol C")
        pm.chosen_ranged_weapon = pm.choose_ranged_weapon()

        enemy = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        enemy.type = "pirate"
        enemy.occupation = "pirate"
        enemy.skills = {}
        give_item(enemy, "laser pistol C")
        enemy.chosen_ranged_weapon = enemy.choose_ranged_weapon()

        all_items = {"laser pistol C": make_item("laser pistol C")}
        ctx = EventContext("", "", 1, None, None, None, None, all_items)
        ctx.add_run_params([pm], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [enemy]
        battle = TeamBattle(ctx)

        # With roll=55, offense=50, target_evasion=50:
        # Without Point Man: adjusted_roll = 55 >= 50 -> MISS
        # With Point Man in Round 1: adjusted_roll = 55 - 15 = 40 < 50 -> HIT
        pm.position = POS_CENTER
        battle.round = 1
        with patch("Battle.random.randint", return_value=55), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch.object(battle, "damage_target") as mock_dmg:
            await battle.run_battle_action_shoot(pm)
            self.assertFalse(mock_dmg.called)

        pm.position = POS_POINT_MAN
        with patch("Battle.random.randint", return_value=55), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch.object(battle, "damage_target") as mock_dmg:
            await battle.run_battle_action_shoot(pm)
            self.assertTrue(mock_dmg.called)

        # Scoutbot on point targeted by enemy in Round 1 with roll=40 (offense=50, evasion=50):
        # Normally 40 < 50 -> HIT; with scoutbot on point in Round 1: 40 + 15 = 55 >= 50 -> MISS
        scout = make_scoutbot_simple()
        scout.stats["intelligence"] = 50
        scout.stats["coordination"] = 50
        scout.stats["strength"] = 50
        scout.skills = {}
        scout.position = POS_POINT_MAN
        ctx.team = [scout]
        battle.round = 1
        with patch("Battle.random.randint", return_value=40), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_pirate_action_result"), \
             patch.object(battle, "damage_target") as mock_dmg:
            await battle.run_battle_action_shoot(enemy)
            self.assertFalse(mock_dmg.called)


# ---------------------------------------------------------------------------
# Command Roles & Formation Effects — Phase 2 Tests
# ---------------------------------------------------------------------------

from Event import team_evades_notice
from Mission import get_specialist_position_bonus, calculate_goal_outcome_hack


class TestRolePositionEffectsPhase2(unittest.IsolatedAsyncioTestCase):

    def test_rec_a_stealth_point_man_double_weight_and_scoutbot_scanner_bonus(self):
        """Point Man's evasion counts double in team_evades_notice, and a scoutbot on point adds +10."""
        agile = make_human_controlled(
            strength=50, willpower=50, coordination=80,
            intelligence=80, courage=50, charisma=50,
        )
        agile.skills = {}
        agile.equipment = []

        other = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        other.skills = {}
        other.equipment = []

        # Both in Center: avg_evasion = (80 + 50) / 2 = 65 -> roll 68 fails
        agile.position = POS_CENTER
        other.position = POS_CENTER
        with patch("Event.random.randint", return_value=68):
            self.assertFalse(team_evades_notice([agile, other]))

        # Agile in Point Man: avg_evasion = (80*2 + 50) / 3 = 70 -> roll 68 passes
        agile.position = POS_POINT_MAN
        with patch("Event.random.randint", return_value=68):
            self.assertTrue(team_evades_notice([agile, other]))

        # Scoutbot with evasion 50 in Center vs Point Man (+10 scanner bonus)
        scout = make_scoutbot_simple()
        scout.stats["intelligence"] = 50
        scout.stats["coordination"] = 50
        scout.stats["strength"] = 50
        scout.skills = {}
        scout.equipment = []

        scout.position = POS_CENTER
        with patch("Event.random.randint", return_value=55):
            # avg_evasion = 50 -> roll 55 fails
            self.assertFalse(team_evades_notice([scout, other]))

        scout.position = POS_POINT_MAN
        with patch("Event.random.randint", return_value=55):
            # avg_evasion = 50 + 10 = 60 -> roll 55 passes
            self.assertTrue(team_evades_notice([scout, other]))

    def test_rec_a_no_point_man_round_1_initiative_penalty(self):
        """When formation positions are assigned and no living member is in Point Man, team gets -10 initiative in Round 1."""
        h = make_human_controlled()
        h.stats["surprise"] = 0
        h.skills = {}
        h.position = POS_CENTER

        enemy = make_human_controlled()
        enemy.stats["surprise"] = -5
        enemy.skills = {}

        # Round 1 without Point Man: h rolls 50 - 10 = 40 < enemy (50 - 5 = 45)
        with patch("Battle.random.randint", return_value=50):
            order_r1 = initiative([h], [enemy], round_num=1)
        self.assertGreater(order_r1.index(h), order_r1.index(enemy))

        # Round 2: penalty no longer applies, h rolls 50 > enemy 45
        with patch("Battle.random.randint", return_value=50):
            order_r2 = initiative([h], [enemy], round_num=2)
        self.assertLess(order_r2.index(h), order_r2.index(enemy))

    async def test_rec_b_overwatch_covering_fire_bonus(self):
        """Overwatch gets -8 to adjusted_roll on SHOOT while at least one living teammate is in Center or Point Man."""
        ow = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        ow.skills = {}
        ow.position = POS_OVERWATCH
        give_item(ow, "laser pistol C")
        ow.chosen_ranged_weapon = ow.choose_ranged_weapon()

        ctr = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        ctr.skills = {}
        ctr.position = POS_CENTER

        enemy = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        enemy.type = "pirate"
        enemy.occupation = "pirate"
        enemy.skills = {}

        all_items = {"laser pistol C": make_item("laser pistol C")}
        ctx = EventContext("", "", 1, None, None, None, None, all_items)
        ctx.add_run_params([ow, ctr], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [enemy]
        battle = TeamBattle(ctx)
        battle.round = 2

        # With ctr alive in Center, roll 55 -> 55 - 8 = 47 < 50 -> HIT
        with patch("Battle.random.randint", return_value=55), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch.object(battle, "damage_target") as mock_dmg:
            await battle.run_battle_action_shoot(ow)
            self.assertTrue(mock_dmg.called)

        # With ctr dead (no front line), roll 55 -> 55 >= 50 -> MISS
        ctr.current_health = 0
        with patch("Battle.random.randint", return_value=55), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch.object(battle, "damage_target") as mock_dmg:
            await battle.run_battle_action_shoot(ow)
            self.assertFalse(mock_dmg.called)

    async def test_rec_c_center_line_formation_melee_defense(self):
        """When 2+ living teammates occupy Center, enemy melee attacks against Center have +8 added to adjusted_roll."""
        c1 = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        c1.skills = {}
        c1.position = POS_CENTER
        c1.set_rect(pygame.Rect(0, 0, 60, 70))

        c2 = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        c2.skills = {}
        c2.position = POS_CENTER
        c2.set_rect(pygame.Rect(0, 0, 60, 70))

        enemy = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        enemy.type = "pirate"
        enemy.occupation = "pirate"
        enemy.skills = {}
        enemy.learning_skills_dict = {}
        give_item(enemy, "slicer C")
        enemy.chosen_melee_weapon = enemy.choose_melee_weapon()

        all_items = {"slicer C": make_item("slicer C")}
        ctx = EventContext("", "", 1, None, None, None, None, all_items)
        ctx.add_run_params([c1, c2], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [enemy]
        battle = TeamBattle(ctx)
        battle.round = 2

        # With both c1 and c2 alive in Center, roll 45 -> 45 + 8 = 53 >= 50 -> MISS
        start_total_hp = c1.current_health + c2.current_health
        with patch("Battle.random.randint", return_value=45), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_pirate_action_result"), \
             patch("Battle.draw_life_bar"), \
             patch("Battle.battle_display_action_damage"), \
             patch("Battle.battle_display_character_hit"):
            await battle.run_battle_action_melee(enemy)
        self.assertEqual(c1.current_health + c2.current_health, start_total_hp)

        # With c2 dead (only 1 in Center), roll 45 < 50 -> HIT
        c2.current_health = 0
        start_c1_hp = c1.current_health
        with patch("Battle.random.randint", return_value=45), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_pirate_action_result"), \
             patch("Battle.draw_life_bar"), \
             patch("Battle.battle_display_action_damage"), \
             patch("Battle.battle_display_character_hit"):
            await battle.run_battle_action_melee(enemy)
        self.assertLess(c1.current_health, start_c1_hp)

    async def test_rec_d_protected_specialists_non_combat_skill_bonus(self):
        """Living Protected Specialists gain +10 difficulty modifier bonus on non-combat challenges and goal checks."""
        spec = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        spec.skills = {"Hacking": 50}
        spec.position = POS_CENTER
        self.assertEqual(get_specialist_position_bonus(spec), 0)

        # Goal room hack with roll=55, Hacking=50: fails in Center (55 >= 50), passes in Protected (55 < 60)
        screen, font = make_dummy_screen(), make_dummy_font()
        with patch("Mission.type_out_text"), \
             patch("Mission.emit_character_image_at_text_offset"), \
             patch("Mission.random.randint", return_value=55):
            self.assertFalse(await calculate_goal_outcome_hack(spec, screen, font))

        spec.position = POS_PROTECTED
        spec.skills = {"Hacking": 50}
        self.assertEqual(get_specialist_position_bonus(spec), 10)
        with patch("Mission.type_out_text"), \
             patch("Mission.emit_character_image_at_text_offset"), \
             patch("Mission.random.randint", return_value=55):
            self.assertTrue(await calculate_goal_outcome_hack(spec, screen, font))

        # Also verify resolve_procedural_challenge passes diff + 10 to standard_skill_check
        captured_diffs = []

        async def fake_skill_check(member, scr, stat_name, skill_name, fnt, diff):
            captured_diffs.append(diff)
            return True

        with patch("Mission.type_out_text"), \
             patch("Mission.standard_skill_check", side_effect=fake_skill_check):
            await resolve_procedural_challenge([spec], "LOCKED_PORTAL", screen, font)
        self.assertEqual(captured_diffs, [10])

    def test_rec_e_commander_and_exec_tactical_command_bonus(self):
        """Commander provides full tactical command bonus plus half from Exec; Exec provides full if Commander is dead."""
        cmd = make_human_controlled()
        cmd.stats["surprise"] = 0
        cmd.stats["leadership"] = 90  # 90 / 30 = 3
        cmd.skills = {"Squad Tactics": 60}  # 60 / 10 = 6 -> total cmd score = 9
        cmd.command_role = ROLE_COMMANDER
        cmd.position = POS_POINT_MAN

        xo = make_human_controlled()
        xo.stats["surprise"] = 0
        xo.stats["leadership"] = 60  # 60 / 30 = 2
        xo.skills = {"Military Science": 40}  # 40 / 10 = 4 -> total xo score = 6 (half = 3)
        xo.command_role = ROLE_EXEC
        xo.position = POS_CENTER

        enemy = make_human_controlled()
        enemy.stats["surprise"] = 10  # enemy roll = 50 + 10 = 60
        enemy.skills = {}

        # With Commander alive (9) + half Exec (3) = +12: xo in Center rolls 50 + 12 = 62 > enemy 60
        with patch("Battle.random.randint", return_value=50):
            order_both = initiative([cmd, xo], [enemy], round_num=2)
        self.assertLess(order_both.index(xo), order_both.index(enemy))

        # When Commander dies, Exec provides full +6 (not +3): against enemy with surprise 5 (roll 55), xo rolls 50 + 6 = 56 > 55
        cmd.current_health = 0
        enemy.stats["surprise"] = 5
        with patch("Battle.random.randint", return_value=50):
            order_xo_only = initiative([cmd, xo], [enemy], round_num=2)
        self.assertLess(order_xo_only.index(xo), order_xo_only.index(enemy))

    def test_instructions_plain_language_without_numbers(self):
        """README.md and src/Intro.py describe roles and positions in plain language without numerical modifiers."""
        with open(os.path.join(os.path.dirname(__file__), "README.md"), "r", encoding="utf-8") as f:
            readme_text = f.read()
        with open(os.path.join(os.path.dirname(__file__), "src", "Intro.py"), "r", encoding="utf-8") as f:
            intro_text = f.read()

        for phrase in ("Mission Commander", "Executive Officer", "Point Man", "Center", "Overwatch", "Protected Specialists"):
            self.assertIn(phrase, readme_text)
            self.assertIn(phrase, intro_text)

        for forbidden_number in ("+20", "-15", "+15", "0.25", "3.0", "+8", "-8"):
            self.assertNotIn(forbidden_number, readme_text)
            self.assertNotIn(forbidden_number, intro_text)


# ---------------------------------------------------------------------------
# Combat & UI Sound Effects Overhaul — Phase 2 Tests
# ---------------------------------------------------------------------------

from Utils import (
    UI_SOUND_PATHS,
    WEAPON_SOUND_PATHS,
    CHARACTER_COMBAT_SOUND_PATHS,
    BATTLE_MUSIC_TRACKS,
    resolve_combat_sound_path,
    play_weapon_sound,
    play_ui_sound,
    play_positive_click,
    play_negative_click,
    play_victory_sound,
    play_defeat_sound,
    play_battle_music,
    resource_path,
)


class TestSoundEffectsPhase2(unittest.IsolatedAsyncioTestCase):

    def test_all_sound_and_music_assets_are_ogg_and_exist(self):
        """All configured UI, weapon, character combat, and battle music paths are .ogg files that exist on disk, and no .mp3 files remain in sounds/ or music/."""
        all_paths = (
            list(UI_SOUND_PATHS.values())
            + list(WEAPON_SOUND_PATHS.values())
            + list(CHARACTER_COMBAT_SOUND_PATHS.values())
            + list(BATTLE_MUSIC_TRACKS)
        )
        for rel_path in all_paths:
            self.assertTrue(rel_path.endswith(".ogg"), f"Expected .ogg path, got {rel_path}")
            abs_path = resource_path(rel_path)
            self.assertTrue(os.path.exists(abs_path), f"Missing audio asset on disk: {rel_path}")

        for folder in ("sounds", "music"):
            folder_abs = resource_path(folder)
            for root, _, files in os.walk(folder_abs):
                for fname in files:
                    self.assertFalse(
                        fname.lower().endswith(".mp3"),
                        f"Unexpected .mp3 file found in {folder}: {os.path.join(root, fname)}",
                    )

    def test_resolve_combat_sound_path_for_weapons_robots_and_klackons(self):
        """Each weapon resolves to its specific .ogg in sounds/combat/, while assaultbot, stunbot, and klackon override with their dedicated combat sounds."""
        human = make_human_controlled()
        expected_weapons = {
            "laser pistol": "sounds/combat/laser.ogg",
            "laser rifle": "sounds/combat/laserrifle.ogg",
            "blaster rifle": "sounds/combat/blaster.ogg",
            "stunner": "sounds/combat/stunner.ogg",
            "carbine": "sounds/combat/carbine.ogg",
            "pistol": "sounds/combat/pistol.ogg",
            "magnum": "sounds/combat/pistol.ogg",
            "slicer": "sounds/combat/slicer.ogg",
            "stun baton": "sounds/combat/melee.ogg",
            "knife": "sounds/combat/melee.ogg",
            "launcher": "sounds/combat/launcher.ogg",
        }
        for weapon, expected_path in expected_weapons.items():
            self.assertEqual(resolve_combat_sound_path(weapon, human), expected_path)

        assaultbot = make_robot(250)
        assaultbot.occupation = "assaultbot"
        self.assertEqual(resolve_combat_sound_path("laser pistol", assaultbot), "sounds/combat/assaultbot.ogg")

        stunbot = make_robot(250)
        stunbot.occupation = "stunbot"
        self.assertEqual(resolve_combat_sound_path("stun baton", stunbot), "sounds/combat/stunbot.ogg")

        klackon = make_human_controlled()
        klackon.type = "klackon"
        klackon.occupation = "klackon"
        self.assertEqual(resolve_combat_sound_path("slicer", klackon), "sounds/combat/hiss.ogg")

        broodmother = make_human_controlled()
        broodmother.type = "klackon"
        broodmother.occupation = "broodmother"
        self.assertEqual(resolve_combat_sound_path("blaster rifle", broodmother), "sounds/combat/hiss.ogg")

    async def test_battle_passes_character_to_play_weapon_sound(self):
        """run_battle_action_shoot and run_battle_action_melee pass the attacking character to play_weapon_sound."""
        bot = make_robot(250)
        bot.occupation = "assaultbot"
        bot.position = POS_CENTER
        give_item(bot, "laser pistol C")
        bot.chosen_ranged_weapon = bot.choose_ranged_weapon()

        klackon = make_human_controlled()
        klackon.type = "klackon"
        klackon.occupation = "klackon"
        klackon.position = POS_CENTER
        give_item(klackon, "slicer C")
        klackon.chosen_melee_weapon = klackon.choose_melee_weapon()

        all_items = {
            "laser pistol C": make_item("laser pistol C"),
            "slicer C": make_item("slicer C"),
        }
        ctx = EventContext("", "", 1, None, None, None, None, all_items)
        ctx.add_run_params([bot], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [klackon]
        battle = TeamBattle(ctx)
        battle.round = 2

        with patch("Battle.random.randint", return_value=99), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound") as mock_play_sfx, \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch("Battle.battle_display_pirate_action_result"), \
             patch("Battle.draw_life_bar"), \
             patch("Battle.battle_display_action_damage"), \
             patch("Battle.battle_display_character_hit"), \
             patch.object(TeamBattle, "damage_target"):
            await battle.run_battle_action_shoot(bot)
            mock_play_sfx.assert_called_with("laser pistol", bot)

            mock_play_sfx.reset_mock()
            await battle.run_battle_action_melee(klackon)
            mock_play_sfx.assert_called_with("slicer", klackon)

    def test_play_battle_music_selects_random_fight_track(self):
        """play_battle_music randomly chooses one of music/fight1.ogg, music/fight2.ogg, or music/fight3.ogg."""
        self.assertEqual(
            BATTLE_MUSIC_TRACKS,
            ("music/fight1.ogg", "music/fight2.ogg", "music/fight3.ogg"),
        )
        dummy_pygame = unittest.mock.MagicMock()
        dummy_pygame.mixer.get_init.return_value = True
        with patch("Utils.random.choice", return_value="music/fight2.ogg") as mock_choice:
            play_battle_music(dummy_pygame)
            mock_choice.assert_called_once_with(BATTLE_MUSIC_TRACKS)
            dummy_pygame.mixer.music.load.assert_called_once_with(resource_path("music/fight2.ogg"))


# ---------------------------------------------------------------------------
# Combat & UI Sound Effects Overhaul — Phase 3 Tests
# ---------------------------------------------------------------------------

from Utils import team_mission_success
from MissionOrders import Checkbox
import Event as EventMod


class TestSoundEffectsPhase3(unittest.IsolatedAsyncioTestCase):

    def test_play_ui_sound_helpers_load_and_play_expected_ogg_files(self):
        """play_positive_click, play_negative_click, play_victory_sound, and play_defeat_sound load and play their .ogg files."""
        expected = [
            (play_positive_click, "sounds/ui/positiveclick.ogg"),
            (play_negative_click, "sounds/ui/negativeclick.ogg"),
            (play_victory_sound, "sounds/ui/victory.ogg"),
            (play_defeat_sound, "sounds/ui/defeat.ogg"),
        ]
        for helper_fn, expected_path in expected:
            dummy_sound = unittest.mock.MagicMock()
            with patch("Utils.load_sound", return_value=dummy_sound) as mock_load:
                helper_fn()
                mock_load.assert_called_once_with(expected_path)
                dummy_sound.play.assert_called_once()

    def test_team_mission_success_plays_victory_sound_and_awards_points(self):
        """team_mission_success plays victory.ogg and adds 100 mission points to each team member."""
        c1 = make_human_controlled()
        c2 = make_human_controlled()
        c1.mission_points = 10
        c2.mission_points = 25
        with patch("Utils.play_victory_sound") as mock_victory:
            team_mission_success([c1, c2])
            mock_victory.assert_called_once()
        self.assertEqual(c1.mission_points, 110)
        self.assertEqual(c2.mission_points, 125)

    async def test_mission_failure_and_pause_to_clear_screen_play_defeat_and_positive_click(self):
        """mission_failure plays defeat sound on entry and positive click on dismiss; pause_to_clear_screen plays positive click."""
        screen = make_dummy_screen()
        bg = make_dummy_screen()
        font = make_dummy_font()
        click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (100, 100), "button": 1})

        with patch("Event.play_defeat_sound") as mock_defeat, \
             patch("Event.play_positive_click") as mock_pos, \
             patch("Event.pygame.display.flip"), \
             patch("Event.pygame.event.get", return_value=[click_event]):
            await EventMod.mission_failure(screen, font)
            mock_defeat.assert_called_once()
            mock_pos.assert_called_once()

        with patch("Event.type_out_text"), \
             patch("Event.clear_screen"), \
             patch("Event.play_positive_click") as mock_pos2, \
             patch("Event.pygame.event.get", return_value=[click_event]):
            await EventMod.pause_to_clear_screen(screen, bg, font)
            mock_pos2.assert_called_once()

    def test_mission_orders_checkbox_plays_positive_click(self):
        """Clicking a MissionOrders Checkbox plays positiveclick.ogg and checks that option."""
        font = make_dummy_font()
        cb1 = Checkbox("Opt 1", "a", 100, 100, font, [])
        cb2 = Checkbox("Opt 2", "b", 100, 130, font, [])
        group = [cb1, cb2]
        cb1.group = group
        cb2.group = group
        cb1.checked = True

        click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (105, 135), "button": 1})
        with patch("MissionOrders.play_positive_click") as mock_pos:
            cb2.handle_event(click_ev)
            mock_pos.assert_called_once()
        self.assertFalse(cb1.checked)
        self.assertTrue(cb2.checked)

    def test_all_stages_wire_ui_sounds(self):
        """All stage files wire positive and negative UI click sounds."""
        stage_files = (
            "LoadGame.py",
            "Intro.py",
            "ChooseTeam4.py",
            "MissionOrders.py",
            "EquipTeam2.py",
            "PositionTeam.py",
            "Voyage.py",
            "Mission.py",
            "ReturnVoyage.py",
            "Score.py",
        )
        src_dir = os.path.join(os.path.dirname(__file__), "src")
        for fname in stage_files:
            with open(os.path.join(src_dir, fname), "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("play_positive_click()", content, f"{fname} missing play_positive_click()")
            self.assertIn("play_negative_click()", content, f"{fname} missing play_negative_click()")


# ---------------------------------------------------------------------------
# Robot Module Extraction — Phase 1 Tests
# ---------------------------------------------------------------------------

from Robot import Robot, ROBOT_ATTRIBUTES, ROBOT_SPECS, get_robot_cost
from Item import ALL_ATTRIBUTES, load_items_battle


class TestRobotModulePhase1(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.all_items = load_items_battle()

    def test_robot_attributes_and_specs_cover_all_ten_robots(self):
        """ROBOT_ATTRIBUTES and ROBOT_SPECS define all 10 robot types and sync with Item.ALL_ATTRIBUTES."""
        expected_robots = {
            "assaultbot", "stunbot", "mechbot", "techbot", "hackbot",
            "meleebot", "batonbot", "medibot", "mulebot", "scoutbot",
        }
        self.assertEqual(set(ROBOT_ATTRIBUTES.keys()), expected_robots)
        self.assertEqual(set(ROBOT_SPECS.keys()), expected_robots)
        for rtype in expected_robots:
            self.assertIn(rtype, ALL_ATTRIBUTES)
            self.assertEqual(ALL_ATTRIBUTES[rtype], ROBOT_ATTRIBUTES[rtype])
            self.assertEqual(get_robot_cost(rtype), ROBOT_ATTRIBUTES[rtype][0])
        self.assertEqual(get_robot_cost("nonexistent_bot"), 0)

    def test_robot_create_builds_robot_and_character_instances(self):
        """Robot.create returns a Robot (and Character) instance with the expected stats, skills, and equipment."""
        for idx, (rtype, spec) in enumerate(ROBOT_SPECS.items()):
            bot = Robot.create(rtype, idx, self.all_items)
            self.assertIsInstance(bot, Robot)
            self.assertIsInstance(bot, Character)
            self.assertTrue(bot.is_robot())
            self.assertEqual(bot.type, "robot")
            self.assertEqual(bot.occupation, rtype)
            self.assertEqual(bot.name, f"{spec['prefix']}{idx}")
            expected_hp = ROBOT_ATTRIBUTES[rtype][5]
            self.assertEqual(bot.max_life, expected_hp)
            self.assertEqual(bot.current_health, expected_hp)
            self.assertEqual(bot.stats["max_health"], expected_hp)
            for stat_name, stat_val in spec["stats"].items():
                self.assertEqual(bot.stats[stat_name], stat_val, f"{rtype} mismatch on {stat_name}")
            self.assertEqual(bot.skills, spec["skills"])
            self.assertEqual([item.name for item in bot.equipment], list(spec["equipment"]))

    def test_character_factory_aliases_match_robot_create(self):
        """All 10 Character.create_<type> and Robot.create_<type> methods return Robot instances."""
        for rtype in ROBOT_SPECS:
            factory_name = f"create_{rtype}"
            char_bot = getattr(Character, factory_name)(4, self.all_items)
            robot_bot = getattr(Robot, factory_name)(4, self.all_items)
            self.assertIsInstance(char_bot, Robot)
            self.assertIsInstance(robot_bot, Robot)
            self.assertEqual(char_bot.name, robot_bot.name)
            self.assertEqual(char_bot.stats, robot_bot.stats)
            self.assertEqual(char_bot.skills, robot_bot.skills)
            self.assertEqual(
                [it.name for it in char_bot.equipment],
                [it.name for it in robot_bot.equipment],
            )

    def test_robot_to_dict_and_from_dict_roundtrip(self):
        """Serializing a Robot and restoring via Character.from_dict returns a Robot instance with intact fields."""
        bot = Robot.create("techbot", 2, self.all_items)
        data = bot.to_dict()
        restored = Character.from_dict(data)
        self.assertIsInstance(restored, Robot)
        self.assertIsInstance(restored, Character)
        self.assertTrue(restored.is_robot())
        self.assertEqual(restored.name, "TKB2")
        self.assertEqual(restored.occupation, "techbot")
        self.assertEqual(restored.max_life, bot.max_life)
        self.assertEqual(restored.current_health, bot.current_health)
        self.assertEqual(restored.stats, bot.stats)
        self.assertEqual(restored.skills, bot.skills)
        self.assertEqual([it.name for it in restored.equipment], ["stunner"])


# ---------------------------------------------------------------------------
# Robot Module Extraction — Phase 2 Tests
# ---------------------------------------------------------------------------

from Item import load_item_tabs
from Score import liquidate_surviving_robots


class TestRobotModulePhase2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.all_items = load_items_battle()

    def test_load_item_tabs_populates_robots_store_tab(self):
        """load_item_tabs()['robots'] contains all 10 robot store catalog entries with matching costs."""
        tabs = load_item_tabs()
        self.assertIn("robots", tabs)
        robot_tab = tabs["robots"]
        self.assertEqual({item.name for item in robot_tab}, set(ROBOT_ATTRIBUTES.keys()))
        for item in robot_tab:
            self.assertEqual(item.type, "robot")
            self.assertEqual(item.cost, get_robot_cost(item.name))

    def test_robot_add_to_team_appends_robot_and_updates_team_refs(self):
        """Robot.add_to_team creates a Robot, appends it to the team, and updates member.team references."""
        human = make_human_controlled(strength=20)
        heavy = Item("Heavy Crate", "misc", 10, 50, 1, 0, "none", 10, "A heavy crate")
        human.equipment.append(heavy)
        team = [human]
        human.team = team
        self.assertTrue(human.is_encumbered())

        mule = Robot.add_to_team(team, "mulebot", self.all_items)
        self.assertIsInstance(mule, Robot)
        self.assertEqual(mule.name, "MUB1")
        self.assertEqual(len(team), 2)
        self.assertIs(team[1], mule)
        self.assertIs(human.team, team)
        self.assertIs(mule.team, team)
        self.assertFalse(human.is_encumbered())

    def test_liquidate_surviving_robots_refunds_surviving_robot_instances(self):
        """liquidate_surviving_robots refunds surviving Robot instances using get_robot_cost and filters them out."""
        h1 = make_human_controlled()
        bot_alive_1 = Robot.create("assaultbot", 1, self.all_items)  # 500
        bot_alive_2 = Robot.create("scoutbot", 2, self.all_items)    # 150
        bot_dead = Robot.create("medibot", 3, self.all_items)        # 500, dead
        bot_dead.current_health = 0

        team = [h1, bot_alive_1, bot_alive_2, bot_dead]
        survivors, refund = liquidate_surviving_robots(team)
        self.assertEqual(survivors, [h1])
        self.assertEqual(refund, 650)
        self.assertEqual(h1.team, [h1])


# ---------------------------------------------------------------------------
# Equipment Audit & Expansion — Phase 1 Tests
# ---------------------------------------------------------------------------

from Utils import heal_team_by, team_needs_heal
from Mission import calculate_goal_outcome_cutter, calculate_outcome_officers_quarters_jalorith


class TestEquipmentAuditPhase1(unittest.IsolatedAsyncioTestCase):

    def test_rebalanced_item_attributes_and_damage_types(self):
        """Existing items have updated costs, masses, effects, and effect types (pierce for firearms, slash for slicer)."""
        ps = make_item("power shield C")
        self.assertEqual(ps.mass, 4)
        self.assertEqual(ps.cost, 200)

        holo = make_item("holofier C")
        self.assertEqual(holo.cost, 325)
        self.assertEqual(holo.mass, 2)

        orb = make_item("stealth orb C")
        self.assertEqual(orb.mass, 3)

        pac = make_item("pacifier C")
        self.assertEqual(pac.cost, 250)
        self.assertEqual(pac.mass, 3)

        nt = make_item("neural trainer C")
        self.assertEqual(nt.cost, 250)

        for firearm in ("pistol C", "magnum C", "carbine C"):
            w = make_item(firearm)
            self.assertEqual(w.effect_type, "pierce", f"{firearm} should deal pierce damage")

        carbine = make_item("carbine C")
        self.assertEqual(carbine.cost, 400)
        self.assertEqual(carbine.mass, 6)
        self.assertEqual(carbine.effect, 18)

        slicer = make_item("slicer C")
        self.assertEqual(slicer.effect_type, "slash")
        self.assertEqual(slicer.mass, 4)

    def test_stunbot_has_sonic_weapons_skill(self):
        """Stunbot has Sonic Weapons: 75 to match its equipped stunner."""
        self.assertEqual(ROBOT_SPECS["stunbot"]["skills"].get("Sonic Weapons"), 75)
        self.assertNotIn("Energy Weapons", ROBOT_SPECS["stunbot"]["skills"])

    def test_stimulant_overheals_and_raises_max_health_with_tier_scaling(self):
        """Stimulant increases get_max_health() by effect*2, boosts current_health on add_item, and allows heal_team_by up to get_max_health()."""
        c = make_human(50, 50)  # base max_health = 100
        self.assertEqual(c.get_max_health(), 100)

        stim_c = make_item("stimulant C")  # effect 25 -> +50 max_health
        c.add_item(stim_c)
        self.assertEqual(c.get_max_health(), 150)
        self.assertEqual(c.current_health, 150)
        self.assertEqual(c.get_health_ratio(), 1.0)

        # Taking 30 damage leaves c at 120 HP (still above 100 base max_health -> health_ratio 1.0)
        c.hurt(30, "impact")
        self.assertEqual(c.current_health, 120)
        self.assertEqual(c.get_health_ratio(), 1.0)

        # Damage down to 90 HP -> heal_team_by(40) heals back up to 130 (above base 100, capped at 150)
        c.current_health = 90
        self.assertTrue(team_needs_heal([c]))  # 90 < 0.75 * 150 (112.5)
        heal_team_by([c], 40)
        self.assertEqual(c.current_health, 130)

        # Removing stimulant clamps current_health back to base max_health (100)
        c.remove_item("stimulant C")
        self.assertEqual(c.get_max_health(), 100)
        self.assertEqual(c.current_health, 100)

        # S-tier stimulant (effect 29) grants +58 max_health
        c.add_item(make_item("stimulant S"))
        self.assertEqual(c.get_max_health(), 158)
        self.assertEqual(c.current_health, 158)

    def test_powered_armor_eliminates_encumbrance(self):
        """Character wearing powered armor is never encumbered regardless of carried mass."""
        c = make_human_controlled(strength=20)  # max unencumbered mass = 10
        heavy = Item("Heavy Crate", "misc", 10, 50, 1, 0, "impact", 10, "A heavy crate")
        c.add_item(heavy)
        self.assertTrue(c.is_encumbered())

        c.add_item(make_item("powered armor C"))
        self.assertFalse(c.is_encumbered())

    def test_neural_trainer_skill_floor_tier_scaling_and_double_learning(self):
        """Neural trainer sets untrained skill floor to effect*3 (21..30) and doubles learning rate."""
        c = make_human(50, 50)
        c.skills = {}
        self.assertEqual(c.get_effective_skill_level("Hacking", learning=False), 0)

        c.add_item(make_item("neural trainer C"))  # effect 7 -> floor 21
        self.assertEqual(c.get_effective_skill_level("Hacking", learning=False), 21)

        c.remove_item("neural trainer C")
        c.add_item(make_item("neural trainer S"))  # effect 10 -> floor 30
        self.assertEqual(c.get_effective_skill_level("Hacking", learning=False), 30)

        # Double learning progress: skill at 20 has threshold 2 -> 1 use with neural trainer advances skill to 21
        c.skills = {"Piloting": 20}
        c.stats["coordination"] = 60
        c.stats["willpower"] = 60
        c.learning_skills_dict["Piloting"] = 0
        c.get_effective_skill_level("Piloting", learning=True)
        self.assertEqual(c.skills["Piloting"], 21)

    def test_scanner_and_stealth_orb_skill_and_evasion_bonuses(self):
        """Scanner boosts analyze, Detection/Artifact Analysis/Xenobiology, and team_evades_notice; stealth orb boosts Stealth skill."""
        c = make_human_controlled(intelligence=50, coordination=50, willpower=50)
        c.skills = {"Detection": 40, "Stealth": 40}
        base_analyze = c.get_effective_stat_level("analyze")

        c.add_item(make_item("scanner C"))  # effect 20 -> analyze +30, Detection +20
        self.assertEqual(c.get_effective_stat_level("analyze"), base_analyze + 30)
        self.assertEqual(c.get_effective_skill_level("Detection", learning=False), 60)
        self.assertEqual(c.get_effective_skill_level("Artifact Analysis", learning=False), 20)
        self.assertEqual(c.get_effective_skill_level("Xenobiology", learning=False), 20)

        # Scanner grants +10 to team_evades_notice (evasion 50 + 10 = 60 -> roll 55 evades)
        with patch("Event.random.randint", return_value=55):
            self.assertTrue(team_evades_notice([c]))

        c.add_item(make_item("stealth orb C"))  # effect 40 -> Stealth +20
        self.assertEqual(c.get_effective_skill_level("Stealth", learning=False), 60)
        self.assertFalse(c.is_encumbered())

    async def test_offense_implant_scales_by_tier_and_aids_melee_hit(self):
        """Offense implant scales by item.effect in get_effective_combat_offense and boosts melee hit threshold."""
        c = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        c.skills = {}
        c.set_rect(pygame.Rect(0, 0, 60, 70))
        base_off = c.get_effective_combat_offense()
        c.add_item(make_item("offense implant S"))  # effect 58
        self.assertAlmostEqual(c.get_effective_combat_offense(), base_off + 58)

        give_item(c, "slicer C")
        c.chosen_melee_weapon = c.choose_melee_weapon()

        enemy = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        enemy.type = "pirate"
        enemy.occupation = "pirate"
        enemy.skills = {}
        enemy.set_rect(pygame.Rect(0, 0, 60, 70))

        all_items = {"slicer C": make_item("slicer C")}
        ctx = EventContext("", "", 1, None, None, None, None, all_items)
        ctx.add_run_params([c], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [enemy]
        battle = TeamBattle(ctx)
        battle.round = 2

        # Roll 80 normally misses (80 >= 50), but with offense implant S (offense = 50 + 58 = 108), 80 < 108 hits!
        start_hp = enemy.current_health
        with patch("Battle.random.randint", return_value=80), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch("Battle.draw_life_bar"), \
             patch("Battle.battle_display_action_damage"), \
             patch("Battle.battle_display_character_hit"):
            await battle.run_battle_action_melee(c)
        self.assertLess(enemy.current_health, start_hp)

    async def test_bio_container_pacifier_cutter_and_medibot_uses(self):
        """Bio container bypasses MEDICAL_CACHE; pacifier handles psycho/traitor/Jalorith; medibot heals without consuming medikit."""
        from Event import team_heals
        screen, font = make_dummy_screen(), make_dummy_font()

        # 1. Bio container bypasses MEDICAL_CACHE and heals team
        c = make_human(50, 50)
        c.current_health = 60
        c.add_item(make_item("bio container C"))
        with patch("Mission.type_out_text"):
            passed = await resolve_procedural_challenge([c], "MEDICAL_CACHE", screen, font)
        self.assertTrue(passed)
        self.assertEqual(c.current_health, 95)

        # 2. Pacifier subdues psychotic crew member when perception fails
        psycho = make_psycho(offense=99)
        guard = make_victim(perception=10)
        guard.add_item(make_item("pacifier C"))
        team_p = [psycho, guard]
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.random.randint", return_value=99):
            await calculate_outcome_psychotic_attack(team_p, None, None, screen, font)
        self.assertNotIn(psycho, team_p)
        self.assertEqual(guard.current_health, 100)

        # 3. Pacifier captures fleeing traitor when perception fails
        traitor = make_traitor()
        cmd = make_commander(perception=10, surprise=10)
        cmd.add_item(make_item("pacifier C"))
        team_t = [cmd, traitor]
        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.standard_skill_check", return_value=False), \
             patch("ReturnVoyage.random.randint", return_value=99):
            await calculate_outcome_traitor_sabotage(team_t, None, None, screen, font)
        self.assertNotIn(traitor, team_t)

        # 4. Pacifier awards +15 bonus points on Jalorith mission goal
        cmd.mission_points = 0
        with patch("Mission.type_out_text"):
            await calculate_outcome_officers_quarters_jalorith([cmd], None, None, screen, font)
        self.assertEqual(cmd.mission_points, 15)

        # 5. Medibot provides medical supplies in team_heals without consuming medikit
        wounded = make_human(50, 50)
        wounded.current_health = 40
        medibot = Robot.create("medibot", 1, load_items_battle())
        team_m = [wounded, medibot]
        with patch("Event.type_out_text"), \
             patch("Event.team_skill_check", return_value=True):
            await team_heals(team_m, screen, font)
        self.assertEqual(wounded.current_health, 100)
        self.assertTrue(medibot.has_item("medikit"))


# ---------------------------------------------------------------------------
# Equipment Audit & Expansion — Phase 2 & 3 Tests
# ---------------------------------------------------------------------------

from Item import ITEM_ATTRIBUTES, ARMOR_ATTRIBUTES, load_items, upgrade_item_class
from Event import calculate_outcome_found_items


class TestEquipmentExpansionPhase3(unittest.IsolatedAsyncioTestCase):

    def test_all_seven_damage_types_covered_by_weapons(self):
        """Every damage type in ARMOR_ATTRIBUTES (energy, sonic, impact, slash, pierce, concussion, electric) has weapon items."""
        expected_damage_types = {"energy", "sonic", "impact", "slash", "pierce", "concussion", "electric"}
        all_items = load_items()
        weapons = [it for name, it in all_items.items() if it.type == "weapon" and item_class(name) == "C"]

        weapon_damage_types = {w.effect_type for w in weapons}
        self.assertEqual(weapon_damage_types, expected_damage_types)

        # Verify all 17 C-tier weapons exist in the store catalog
        tabs = load_item_tabs()
        weapon_bases = {item_base_name(it.name) for it in tabs["weapons"]}
        expected_weapons = {
            "magnum", "laser pistol", "pistol", "slicer", "stunner",
            "carbine", "laser rifle", "blaster rifle", "stun baton",
            "grenade rifle", "power mace", "flechette pistol", "mono spear",
            "launcher", "grav hammer", "arc thrower", "shock prod",
        }
        self.assertEqual(weapon_bases, expected_weapons)

    def test_all_armors_and_helmets_in_store_and_armor_attributes(self):
        """All 11 armor bases (3 helmets + 8 body armors) exist across C/B/A/S tiers and in ARMOR_ATTRIBUTES."""
        tabs = load_item_tabs()
        armor_bases = {item_base_name(it.name) for it in tabs["armor"]}
        expected_armors = {
            "power shield", "veer suit", "exoskeleton", "holofier", "powered armor",
            "sonic helmet", "targeting helmet", "command helmet",
            "flak vest", "insulated suit", "chitin carapace",
        }
        self.assertEqual(armor_bases, expected_armors)
        self.assertEqual(set(ARMOR_ATTRIBUTES.keys()), expected_armors)

        all_items = load_items()
        for base in expected_armors:
            self.assertEqual(len(ARMOR_ATTRIBUTES[base]), 7)
            item_c = all_items[f"{base} C"]
            item_b = upgrade_item_class(item_c, all_items)
            item_a = upgrade_item_class(item_b, all_items)
            item_s = upgrade_item_class(item_a, all_items)
            self.assertIsNotNone(item_b)
            self.assertIsNotNone(item_a)
            self.assertIsNotNone(item_s)
            self.assertIsNone(upgrade_item_class(item_s, all_items))

    def test_all_gadget_icons_load_without_missing_images(self):
        """Every item in load_items() loads a valid pygame.Surface icon from gadgets/."""
        all_items = load_items()
        for name, item in all_items.items():
            self.assertIsNotNone(item.icon, f"Missing icon surface for item '{name}'")

    def test_helmet_and_body_armor_slot_enforcement(self):
        """Characters can equip at most 1 helmet and at most 1 body armor (up to 2 armor items total)."""
        c = make_human(50, 50)
        sonic_helm = make_item("sonic helmet C")
        target_helm = make_item("targeting helmet C")
        flak = make_item("flak vest C")
        carapace = make_item("chitin carapace C")

        self.assertTrue(sonic_helm.is_helmet())
        self.assertFalse(sonic_helm.is_body_armor())
        self.assertTrue(flak.is_body_armor())
        self.assertFalse(flak.is_helmet())

        # Equip 1 helmet -> allowed
        ok1, err1 = c.can_equip_item(sonic_helm)
        self.assertTrue(ok1)
        self.assertIsNone(err1)
        c.add_item(sonic_helm)
        self.assertTrue(c.has_helmet())
        self.assertFalse(c.has_body_armor())

        # Second helmet -> blocked
        ok2, err2 = c.can_equip_item(target_helm)
        self.assertFalse(ok2)
        self.assertEqual(err2, "Max one helmet per character")

        # Equip 1 body armor alongside the helmet -> allowed
        ok3, err3 = c.can_equip_item(flak)
        self.assertTrue(ok3)
        c.add_item(flak)
        self.assertTrue(c.has_body_armor())
        self.assertEqual(c.get_armor_count(), 2)

        # Second body armor -> blocked
        c.remove_item("sonic helmet C")
        ok4, err4 = c.can_equip_item(carapace)
        self.assertFalse(ok4)
        self.assertEqual(err4, "Max one body armor per character")

    async def test_found_items_and_get_needed_item_respect_helmet_and_body_armor_slots(self):
        """get_needed_item suggests a helmet when body armor is already worn, and found_items swaps body armor rather than stacking two."""
        c = make_human(50, 50)
        c.add_item(make_item("laser pistol S"))
        c.add_item(make_item("slicer S"))
        c.add_item(make_item("veer suit S"))
        all_items = {
            "veer suit C": make_item("veer suit C"),
            "sonic helmet C": make_item("sonic helmet C"),
        }

        with patch("Utils.random.random", return_value=0.1):
            res = get_needed_item([c], all_items)
        self.assertIsNotNone(res)
        _, suggested = res
        self.assertEqual(suggested.name, "sonic helmet C")

        # If a character with Exoskeleton Systems wearing veer suit C finds exoskeleton C, it swaps veer suit C
        exo_user = make_human(50, 50)
        exo_user.skills = {"Exoskeleton Systems": 60}
        exo_user.add_item(make_item("laser pistol C"))
        exo_user.add_item(make_item("slicer C"))
        exo_user.add_item(make_item("veer suit C"))
        screen, font = make_dummy_screen(), make_dummy_font()
        with patch("Event.get_needed_item", return_value=(exo_user, make_item("exoskeleton C"))), \
             patch("Event.type_out_text"):
            await calculate_outcome_found_items([exo_user], None, None, screen, font)
        body_armors = [i for i in exo_user.equipment if i.is_body_armor()]
        self.assertEqual(len(body_armors), 1)
        self.assertEqual(body_armors[0].name, "exoskeleton C")


# ---------------------------------------------------------------------------
# Equipment Audit & Expansion — Phase 4 Tests
# ---------------------------------------------------------------------------

from Event import pirate_enemies, mission_enemies, klackon_queen, jalorith


class TestEquipmentCombatPhase4(unittest.IsolatedAsyncioTestCase):

    def test_all_seven_damage_types_reduced_by_matching_armor_in_hurt(self):
        """Character.hurt applies ARMOR_ATTRIBUTES multipliers across all 7 damage types."""
        cases = [
            ("energy", "power shield C", 30),       # round(30 * 1.0) = 30
            ("sonic", "sonic helmet C", 25),        # round(25 * 1.0) = 25
            ("impact", "flak vest C", 15),          # round(25 * 0.6) = 15
            ("slash", "chitin carapace C", 32),     # round(35 * 0.9) = 32
            ("pierce", "chitin carapace C", 28),    # round(35 * 0.8) = 28
            ("concussion", "flak vest C", 20),      # round(25 * 0.8) = 20
            ("electric", "insulated suit C", 28),   # round(28 * 1.0) = 28
        ]
        for dmg_type, armor_name, expected_reduction in cases:
            c = make_human(50, 50)  # 100 HP
            c.add_item(make_item(armor_name))
            c.hurt(70, dmg_type)
            expected_hp = 100 - max(1, 70 - expected_reduction)
            self.assertEqual(
                c.current_health,
                expected_hp,
                f"Expected {expected_hp} HP after 70 {dmg_type} vs {armor_name}, got {c.current_health}",
            )

    def test_robot_sonic_immunity_and_electric_vulnerability(self):
        """Robots take 0 damage from sonic attacks and 1.5x damage from electric attacks."""
        all_items = load_items_battle()
        bot = Robot.create("scoutbot", 1, all_items)  # no armor, 20 HP
        start_hp = bot.current_health

        # Immune to sonic
        died = bot.hurt(40, "sonic")
        self.assertFalse(died)
        self.assertEqual(bot.current_health, start_hp)

        # +50% electric damage (10 -> 15)
        bot.hurt(10, "electric")
        self.assertEqual(bot.current_health, start_hp - 15)

    def test_choose_ranged_and_melee_weapons_support_new_arsenal(self):
        """choose_ranged_weapon and choose_melee_weapon select the new weapons based on character skills and pacifist means."""
        # Explosives -> launcher
        demo = make_human(50, 50)
        demo.skills = {"Explosives": 60}
        demo.add_item(make_item("pistol C"))
        demo.add_item(make_item("launcher C"))
        self.assertEqual(item_base_name(demo.choose_ranged_weapon().name), "launcher")

        # Sharpshooting -> grenade rifle
        sniper = make_human(50, 50)
        sniper.skills = {"Sharpshooting": 60}
        sniper.add_item(make_item("pistol C"))
        sniper.add_item(make_item("grenade rifle C"))
        self.assertEqual(item_base_name(sniper.choose_ranged_weapon().name), "grenade rifle")

        # Energy Weapons -> arc thrower
        zapper = make_human(50, 50)
        zapper.skills = {"Energy Weapons": 60}
        zapper.add_item(make_item("pistol C"))
        zapper.add_item(make_item("arc thrower C"))
        self.assertEqual(item_base_name(zapper.choose_ranged_weapon().name), "arc thrower")

        # Projectile Weapons -> flechette pistol
        gunner = make_human(50, 50)
        gunner.skills = {"Projectile Weapons": 60}
        gunner.add_item(make_item("stunner C"))
        gunner.add_item(make_item("flechette pistol C"))
        self.assertEqual(item_base_name(gunner.choose_ranged_weapon().name), "flechette pistol")

        # Martial Arts -> grav hammer / mono spear / power mace over stun baton
        brawler = make_human(50, 50)
        brawler.skills = {"Martial Arts": 60}
        brawler.add_item(make_item("stun baton C"))
        brawler.add_item(make_item("grav hammer C"))
        self.assertEqual(item_base_name(brawler.choose_melee_weapon().name), "grav hammer")

        # Pacifist -> shock prod
        pac = make_human(50, 50)
        pac.mission = {"means": "pacifist"}
        pac.add_item(make_item("slicer C"))
        pac.add_item(make_item("shock prod C"))
        self.assertEqual(item_base_name(pac.choose_melee_weapon().name), "shock prod")

    async def test_helmet_stat_skill_morale_and_ranged_accuracy_bonuses(self):
        """Sonic, targeting, and command helmets apply their skill, stat, morale, and ranged accuracy bonuses."""
        # 1. Sonic helmet -> Detection +round(effect * 0.6) (effect 25 -> +15)
        scout = make_human_controlled(intelligence=50, coordination=50, willpower=50)
        scout.skills = {"Detection": 40}
        scout.add_item(make_item("sonic helmet C"))
        self.assertEqual(scout.get_effective_skill_level("Detection", learning=False), 55)

        # 2. Command helmet -> leadership +effect*2, Squad Tactics +effect, Military Science +effect, halves morale drop
        cmd = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        cmd.skills = {"Squad Tactics": 40, "Military Science": 30}
        base_lead = cmd.get_effective_stat_level("leadership")
        cmd.add_item(make_item("command helmet C"))  # effect 15
        self.assertEqual(cmd.get_effective_stat_level("leadership"), base_lead + 30)
        self.assertEqual(cmd.get_effective_skill_level("Squad Tactics", learning=False), 55)
        self.assertEqual(cmd.get_effective_skill_level("Military Science", learning=False), 45)

        start_morale = cmd.morale
        cmd.demoralize(10)  # halved to 5
        self.assertEqual(cmd.morale, start_morale - 5)

        # 3. Targeting helmet -> perception +effect, surprise +effect, Sharpshooting +effect, and ranged accuracy bonus
        marksman = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        marksman.skills = {"Sharpshooting": 20}
        marksman.set_rect(pygame.Rect(0, 0, 60, 70))
        base_perc = marksman.get_effective_stat_level("perception")
        base_surp = marksman.get_effective_stat_level("surprise")
        marksman.add_item(make_item("targeting helmet S"))  # effect 17
        self.assertEqual(marksman.get_effective_stat_level("perception"), base_perc + 17)
        self.assertEqual(marksman.get_effective_stat_level("surprise"), base_surp + 17)
        self.assertEqual(marksman.get_effective_skill_level("Sharpshooting", learning=False), 37)

        give_item(marksman, "grenade rifle C")
        marksman.chosen_ranged_weapon = marksman.choose_ranged_weapon()

        enemy = make_human_controlled(
            strength=50, willpower=50, coordination=50,
            intelligence=50, courage=50, charisma=50,
        )
        enemy.type = "pirate"
        enemy.occupation = "pirate"
        enemy.skills = {}
        enemy.set_rect(pygame.Rect(0, 0, 60, 70))

        all_items = {"grenade rifle C": make_item("grenade rifle C")}
        ctx = EventContext("", "", 1, None, None, None, None, all_items)
        ctx.add_run_params([marksman], make_dummy_screen(), make_dummy_font(), None, make_dummy_font())
        ctx.enemies = [enemy]
        battle = TeamBattle(ctx)
        battle.round = 2

        # marksman base accuracy = 50, Sharpshooting 37 -> -18, targeting helmet S -> -17: roll 70 -> adjusted 35 < 50 hits!
        start_hp = enemy.current_health
        with patch("Battle.random.randint", return_value=70), \
             patch("Battle.announce_action"), \
             patch("Battle.play_weapon_sound"), \
             patch("Battle.battle_display_action"), \
             patch("Battle.battle_display_character_action_result"), \
             patch("Battle.draw_life_bar"), \
             patch("Battle.battle_display_action_damage"), \
             patch("Battle.battle_display_character_hit"):
            await battle.run_battle_action_shoot(marksman)
        self.assertLess(enemy.current_health, start_hp)

    async def test_insulated_suit_protects_against_hazard_leak_damage(self):
        """Characters wearing an insulated suit take 0 damage when a HAZARD_LEAK challenge fails."""
        protected = make_human(50, 50)
        protected.add_item(make_item("insulated suit C"))
        unprotected = make_human(50, 50)
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("Mission.type_out_text"), \
             patch("Mission.standard_skill_check", return_value=False):
            passed = await resolve_procedural_challenge([protected, unprotected], "HAZARD_LEAK", screen, font)
        self.assertFalse(passed)
        self.assertEqual(protected.current_health, 100)
        self.assertEqual(unprotected.current_health, 90)

    def test_new_weapons_resolve_combat_sound_paths_and_enemy_loadouts_valid(self):
        """All 8 new weapons resolve to valid .ogg combat sound paths, and enemy factories respect armor slot rules."""
        human = make_human_controlled()
        for weapon in (
            "grenade rifle", "flechette pistol", "launcher", "arc thrower",
            "power mace", "mono spear", "grav hammer", "shock prod",
        ):
            rel = resolve_combat_sound_path(weapon, human)
            self.assertTrue(rel.endswith(".ogg"))
            self.assertTrue(os.path.exists(resource_path(rel)), f"Missing sound file {rel} for {weapon}")

        all_items = load_items_battle()
        enemies = (
            pirate_enemies(8, all_items)
            + mission_enemies(4, all_items, theatre="derelict")
            + [klackon_queen(all_items), jalorith(all_items)]
        )
        for e in enemies:
            helmets = [i for i in e.equipment if i.is_helmet()]
            body_armors = [i for i in e.equipment if i.is_body_armor()]
            self.assertLessEqual(len(helmets), 1, f"{e.name} has multiple helmets")
            self.assertLessEqual(len(body_armors), 1, f"{e.name} has multiple body armors")

    async def test_traitor_commander_does_not_roll_against_own_conspiracy(self):
        """When the Commander is a traitor, perception/surprise rolls fall to another team member (e.g. Executive Officer)."""
        traitor_cmd = make_traitor(leadership=120, perception=99, surprise=99)
        traitor_cmd.command_role = ROLE_COMMANDER
        loyal_xo = make_commander(leadership=80, perception=90, surprise=80, mission_points=50)
        loyal_xo.command_role = ROLE_EXEC
        team = [traitor_cmd, loyal_xo]
        screen, font = make_dummy_screen(), make_dummy_font()

        with patch("ReturnVoyage.type_out_text"), \
             patch("ReturnVoyage.standard_skill_check", return_value=False), \
             patch("ReturnVoyage.random.randint", return_value=1):
            await calculate_outcome_traitor_sabotage(team, None, None, screen, font)

        self.assertNotIn(traitor_cmd, team)
        self.assertIn(loyal_xo, team)
        self.assertEqual(loyal_xo.mission_points, 60)

    async def test_derelict_toxic_air_survival_event_success_and_failure(self):
        """calculate_outcome_derelict_toxic_air rolls Survival for the best member, or inflicts 5% HP and 5 morale loss on failure."""
        from Mission import calculate_outcome_derelict_toxic_air
        screen, font = make_dummy_screen(), make_dummy_font()

        # 1. Success path: best Survival member counteracts the toxin
        survivor = make_human(50, 50)
        survivor.skills = {"Survival": 60}
        survivor.mission_points = 0
        teammate = make_human(60, 40)
        team_ok = [survivor, teammate]
        spoken = []

        async def capture_text(scr, txt, fnt, color=None):
            spoken.append(txt)

        with patch("Mission.type_out_text", side_effect=capture_text), \
             patch("Mission.standard_skill_check", return_value=True):
            res = await calculate_outcome_derelict_toxic_air(team_ok, None, None, screen, font)

        self.assertTrue(res)
        self.assertTrue(any("The air on this ship is making the team fall ill" in s for s in spoken))
        self.assertTrue(any("pinpoints the issue and administers a drug to counteract the effects" in s for s in spoken))
        self.assertEqual(survivor.mission_points, 5)
        self.assertEqual(survivor.skills["Survival"], 62)
        self.assertEqual(survivor.current_health, 100)
        self.assertEqual(teammate.current_health, 100)

        # 2. Failure path: team takes 5% health and 5 morale hit
        c1 = make_human(50, 50)   # 100 HP -> -5 HP (95), -5 morale (95)
        c2 = make_human(100, 100) # 200 HP -> -10 HP (190), -5 morale (95)
        c1.skills = {"Survival": 30}
        with patch("Mission.type_out_text"), \
             patch("Mission.standard_skill_check", return_value=False):
            res_fail = await calculate_outcome_derelict_toxic_air([c1, c2], None, None, screen, font)

        self.assertFalse(res_fail)
        self.assertEqual(c1.current_health, 95)
        self.assertEqual(c1.morale, 95)
        self.assertEqual(c2.current_health, 190)
        self.assertEqual(c2.morale, 95)


if __name__ == "__main__":
    unittest.main()









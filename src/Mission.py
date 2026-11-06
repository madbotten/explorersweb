
import pygame
import asyncio
import os
import sys

from Character import *
from Item import *
from Location import *
from Utils import *
from Event import *
from TypeText import *
from MissionOrders import MISSION_GOALS, DERELICT_MISSION_GOALS, get_theatre_for_loop, get_mission_goals_for_theatre
from constants import TOP_BAR_Y, DEBUG

# Screen settings
TEXT_AREA_WIDTH = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 8  # Adjust for 8 characters, reserving space for credits

no_suitable_statements = [
    "However, no one on the team is trained to handle this.",
    "No one has any skills or items to apply to the task.",
    "The team isn't equipped to handle this problem effectively.",
    "There isn't anyone with the necessary expertise.",
    "No one on the team possesses the necessary skills.",
]

global locations
global mission_failed
global rooms_to_goal

async def update_screen(surface, background, hour, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"HOUR {hour}", True, CYAN)
    surface.blit(day_text, (40, 10))
    ship_text = font.render("Searching the mission point", True, CYAN)
    surface.blit(ship_text, (120, 10))
    reset_text_offsets()

async def calculate_outcome_sickbay(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} grabs a unkeyed medikit from the corner.", font)
    return


CHALLENGE_ARCHETYPES = {
    "LOCKED_PORTAL": {
        "intro": "A reinforced security portal blocks the passage ahead.",
        "approaches": [
            {"item": "cutter", "success_text": "The team uses the cutter to breach the portal."},
            {
                "stat": None,
                "skill": "Hacking",
                "diff": 0,
                "attempt_text": "tries to hack the controller:",
                "success_text": "gets access and opens the portal.",
                "fail_text": "could not break in.",
            },
            {
                "stat": None,
                "skill": "Ships Systems",
                "diff": 0,
                "attempt_text": "tries to route around the portal controller:",
                "success_text": "reroutes power and opens the portal.",
                "fail_text": "could not reroute the control.",
            },
            {
                "stat": None,
                "skill": "Explosives",
                "diff": 0,
                "attempt_text": "prepares a small charge to blow out the lock:",
                "success_text": "gets the portal open.",
                "fail_text": "could not blow out the lock.",
            },
        ],
        "reward": {"type": "points", "points": 5},
        "penalty": {
            "type": "detour",
            "amount": 2,
            "text": "The portal remains locked, the team must take another route",
        },
    },
    "SECURITY_GRID": {
        "intro": "An active laser and motion-sensor grid sweeps the area.",
        "approaches": [
            {"robot": "hackbot", "success_text": "The team's hackbot interfaces with the junction box and disables the security grid."},
            {
                "stat": "coordination",
                "skill": "Stealth",
                "diff": 0,
                "attempt_text": "attempts to slip past the sensor sweeps and disable the emitter:",
                "success_text": "deactivates the grid undetected!",
                "fail_text": "trips a secondary sensor beam.",
            },
            {
                "stat": "intelligence",
                "skill": "Espionage",
                "diff": 0,
                "attempt_text": "analyzes the security cycling pattern:",
                "success_text": "spoofs the sensor telemetry and clears a path!",
                "fail_text": "cannot bypass the encryption.",
            },
            {
                "stat": "intelligence",
                "skill": "Hacking",
                "diff": -5,
                "attempt_text": "attempts to override the security node:",
                "success_text": "shuts down the grid!",
                "fail_text": "is locked out of the security node.",
            },
        ],
        "reward": {"type": "shortcut", "amount": 1, "points": 5},
        "penalty": {
            "type": "damage_all",
            "amount": 8,
            "text": "Automated defense turrets graze the squad before they can retreat! (-8 HP each)",
        },
    },
    "INTEL_CONSOLE": {
        "intro": "The team discovers an active terminal logged into the stronghold's network.",
        "approaches": [
            {"robot": "hackbot", "success_text": "The team's hackbot siphons encrypted data files from the terminal."},
            {
                "stat": "intelligence",
                "skill": "Hacking",
                "diff": 0,
                "attempt_text": "steps up to hack into the console:",
                "success_text": "gets access and downloads valuable intelligence!",
                "fail_text": "could not break past the firewall.",
            },
            {
                "stat": "intelligence",
                "skill": "Artifact Analysis",
                "diff": 0,
                "attempt_text": "examines the foreign data architecture:",
                "success_text": "extracts secret operational logs!",
                "fail_text": "could not decipher the logs.",
            },
            {
                "stat": "intelligence",
                "skill": "Espionage",
                "diff": 0,
                "attempt_text": "searches the terminal for command codes:",
                "success_text": "copies the stronghold's secret dispatches!",
                "fail_text": "finds only wiped directories.",
            },
        ],
        "reward": {"type": "points", "points": 10},
        "penalty": {
            "type": "none",
            "text": "The terminal locks down before any useful data can be recovered.",
        },
    },
    "HAZARD_LEAK": {
        "intro": "Ruptured conduits fill the chamber with volatile coolant and arcing power lines.",
        "approaches": [
            {
                "stat": "intelligence",
                "skill": "Ships Systems",
                "diff": 0,
                "attempt_text": "rushes to isolate the ruptured manifold:",
                "success_text": "seals the leak and stabilizes the chamber!",
                "fail_text": "cannot close the jammed pressure valve.",
            },
            {
                "stat": "coordination",
                "skill": "Mechanics",
                "diff": 0,
                "attempt_text": "attempts to clamp and patch the damaged conduit:",
                "success_text": "repairs the ruptured line!",
                "fail_text": "is driven back by scalding vapor.",
            },
            {
                "stat": "willpower",
                "skill": "Survival",
                "diff": 0,
                "attempt_text": "guides the team through the safest ventilation pockets:",
                "success_text": "leads everyone safely through the hazard!",
                "fail_text": "cannot avoid the toxic fumes.",
            },
        ],
        "reward": {"type": "points", "points": 5},
        "penalty": {
            "type": "damage_all",
            "amount": 10,
            "text": "Volatile fumes and electrical arcs scorch the team! (-10 HP each)",
        },
    },
    "MEDICAL_CACHE": {
        "intro": "A sealed trauma station contains intact medical supplies.",
        "approaches": [
            {"robot": "medibot", "success_text": "The team's medibot unlocks the trauma station and administers treatment."},
            {"item": "bio container", "success_text": "The team uses a rugged bio container to safely extract and stabilize the restorative compounds."},
            {
                "stat": "intelligence",
                "skill": "Medicine",
                "diff": 0,
                "attempt_text": "unlocks the medical dispensation unit:",
                "success_text": "synthesizes restorative compounds for the squad!",
                "fail_text": "cannot calibrate the unfamiliar medical dispenser.",
            },
            {
                "stat": "intelligence",
                "skill": "Xenobiology",
                "diff": 0,
                "attempt_text": "tests the bio-reagents for human compatibility:",
                "success_text": "prepares a safe restorative dose for the team!",
                "fail_text": "deems the reagents too unstable to use.",
            },
        ],
        "reward": {"type": "heal", "amount": 35, "points": 4},
        "penalty": {
            "type": "none",
            "text": "Without medical expertise, the sealed trauma station cannot be safely used.",
        },
    },
    "CYBER_IMPLANT_BAY": {
        "intro": "An automated cybernetic augmentation pod hums in the corner.",
        "approaches": [
            {
                "stat": "intelligence",
                "skill": "Cybernetics",
                "diff": 0,
                "attempt_text": "reprograms the augmentation pod for a safe neural boost:",
                "success_text": "completes a clean cybernetic tune-up!",
                "fail_text": "aborts the sequence before the pod malfunctions.",
            },
            {
                "stat": "intelligence",
                "skill": "Medicine",
                "diff": -5,
                "attempt_text": "carefully monitors the bio-interface protocols:",
                "success_text": "safely applies the neural enhancement!",
                "fail_text": "shuts the pod down to avoid neural feedback.",
            },
        ],
        "reward": {"type": "stat_boost", "stat": "coordination", "amount": 3, "points": 5},
        "penalty": {
            "type": "demoralize",
            "amount": 4,
            "text": "A painful static shock from the pod rattles the crew's nerves. (-4 morale each)",
        },
    },
    "SUPPLY_LOCKER": {
        "intro": "A heavy ordnance locker sits secured behind biometric clamps.",
        "approaches": [
            {"item": "cutter", "success_text": "The team slices through the locker's biometric clamps with a cutter."},
            {
                "stat": "coordination",
                "skill": "Mechanics",
                "diff": 0,
                "attempt_text": "works to disassemble the locking mechanism:",
                "success_text": "pops the heavy locker open!",
                "fail_text": "cannot budge the reinforced pins.",
            },
            {
                "stat": "coordination",
                "skill": "Tinkering",
                "diff": 0,
                "attempt_text": "tinkers with the electronic latch:",
                "success_text": "bypasses the biometric lock!",
                "fail_text": "shorts out the latch.",
            },
            {
                "stat": "intelligence",
                "skill": "Supply Logistics",
                "diff": 0,
                "attempt_text": "cross-references the depot manifest codes:",
                "success_text": "enters the master supply override code!",
                "fail_text": "finds the manifest codes are outdated.",
            },
        ],
        "reward": {"type": "found_item", "points": 5},
        "penalty": {
            "type": "none",
            "text": "The ordnance locker remains sealed tight.",
        },
    },
    "CAPTIVE_CELL": {
        "intro": "A detained merchant crew member signals from behind a force-field cell.",
        "approaches": [
            {
                "stat": "intelligence",
                "skill": "Hacking",
                "diff": 0,
                "attempt_text": "hacks the detention block control panel:",
                "success_text": "drops the force field and frees the captive!",
                "fail_text": "triggers a cell-block lockout.",
            },
            {
                "stat": "charisma",
                "skill": "Social Engineering",
                "diff": 0,
                "attempt_text": "uses a captured comm-link to spoof a guard transfer order:",
                "success_text": "tricks the automated warden into releasing the cell!",
                "fail_text": "is challenged by security verification.",
            },
            {
                "stat": "charisma",
                "skill": "Interrogation",
                "diff": 0,
                "attempt_text": "questions the captive through the field for intel on the base layout:",
                "success_text": "learns a hidden maintenance route from the grateful captive!",
                "fail_text": "cannot make out their panicked directions.",
            },
        ],
        "reward": {"type": "shortcut", "amount": 1, "points": 8},
        "penalty": {
            "type": "demoralize",
            "amount": 5,
            "text": "Unable to drop the force field in time, the team is forced to leave the cells behind. (-5 morale each)",
        },
    },
}


async def _apply_challenge_reward(team, actor, reward, screen, font):
    global rooms_to_goal
    if not reward:
        return
    points = reward.get("points", 0)
    if points and actor is not None:
        actor.mission_points += points

    rtype = reward.get("type", "points")
    if rtype == "shortcut":
        amt = reward.get("amount", 1)
        rooms_to_goal = max(0, globals().get("rooms_to_goal", 5) - amt)
        await type_out_text(
            screen,
            f"The team discovers a shortcut deeper into the stronghold! (-{amt} room to objective)",
            font,
            GREEN,
        )
    elif rtype == "heal":
        amt = reward.get("amount", 30)
        heal_team_by(team, amt)
        await type_out_text(
            screen,
            f"The medical supplies restore the squad's vitality. (+{amt} HP to team)",
            font,
            GREEN,
        )
    elif rtype == "stat_boost":
        stat_name = reward.get("stat", "coordination")
        amt = reward.get("amount", 3)
        target = actor or next((m for m in team if m.is_alive() and not m.is_robot()), None)
        if target:
            target.increase_stat(stat_name, amt)
            await type_out_text(
                screen,
                f"{target.name}'s {stat_name} is enhanced! (+{amt} {stat_name})",
                font,
                GREEN,
            )
    elif rtype == "found_item":
        await calculate_outcome_found_items(team, None, None, screen, font)


async def _apply_challenge_penalty(team, penalty, screen, font):
    global rooms_to_goal
    if not penalty:
        return
    ptype = penalty.get("type", "none")
    text = penalty.get("text", "The team fails to overcome the obstacle.")
    color = RED if ptype != "none" else WHITE
    await type_out_text(screen, text, font, color)

    if ptype == "detour":
        amt = penalty.get("amount", 2)
        rooms_to_goal = globals().get("rooms_to_goal", 5) + amt
    elif ptype == "damage_all":
        amt = penalty.get("amount", 10)
        for m in team:
            if m and m.is_alive() and not m.has_item("insulated suit"):
                m.hurt(amt, "impact")
    elif ptype == "demoralize":
        amt = penalty.get("amount", 5)
        for m in team:
            if m and m.is_alive() and not m.is_robot():
                m.demoralize(amt)


def get_specialist_position_bonus(member) -> int:
    """Return +10 difficulty modifier if *member* is alive and in the Protected Specialists position."""
    if member is not None and member.is_alive() and getattr(member, "position", None) == "protected":
        return 10
    return 0


async def resolve_procedural_challenge(team, archetype_key, screen, font):
    """Universal multi-approach challenge resolver driven by CHALLENGE_ARCHETYPES."""
    archetype = CHALLENGE_ARCHETYPES[archetype_key]
    intro = archetype.get("intro")
    if intro:
        await type_out_text(screen, intro, font, WHITE)

    attempted_any = False
    for approach in archetype.get("approaches", []):
        if "item" in approach:
            item_name = approach["item"]
            if team_has_item(team, item_name):
                actor = next(
                    (m for m in team if m and m.is_alive() and m.has_item(item_name)),
                    team[0] if team else None,
                )
                await type_out_text(
                    screen,
                    approach.get("success_text", f"The team uses the {item_name} to bypass the obstacle."),
                    font,
                    GREEN,
                )
                await _apply_challenge_reward(team, actor, archetype.get("reward"), screen, font)
                reset_x_offset()
                return True

        elif "robot" in approach:
            robot_name = approach["robot"]
            has_robot = team_has_item(team, robot_name) or any(
                m is not None
                and m.is_alive()
                and (getattr(m, "occupation", "").lower() == robot_name.lower()
                     or getattr(m, "name", "").lower() == robot_name.lower())
                for m in team
            )
            if has_robot:
                actor = next(
                    (m for m in team if m and m.is_alive() and not m.is_robot()),
                    team[0] if team else None,
                )
                await type_out_text(
                    screen,
                    approach.get("success_text", f"The team's {robot_name} handles the task effortlessly."),
                    font,
                    GREEN,
                )
                await _apply_challenge_reward(team, actor, archetype.get("reward"), screen, font)
                reset_x_offset()
                return True

        else:
            stat_name = approach.get("stat")
            skill_name = approach.get("skill")
            member = determine_best_team_member(team, stat_name, skill_name)
            if member:
                diff = approach.get("diff", 0) + get_specialist_position_bonus(member)
                attempted_any = True
                attempt_text = approach.get("attempt_text", f"attempts to use {skill_name or stat_name}:")
                await type_out_text(screen, f"{member.name} {attempt_text}", font)
                check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, diff)
                if check_passed:
                    success_text = approach.get("success_text", "succeeds!")
                    await type_out_text(
                        screen,
                        f"{member.name} {success_text}\nTheir skill has been strengthened.",
                        font,
                        GREEN,
                    )
                    if skill_name:
                        member.increase_skill(skill_name, 2)
                    if stat_name:
                        member.increase_stat(stat_name, 1)
                    await _apply_challenge_reward(team, member, archetype.get("reward"), screen, font)
                    reset_x_offset()
                    return True
                else:
                    fail_text = approach.get("fail_text", "could not succeed.")
                    await type_out_text(screen, f"{member.name} {fail_text}", font, WHITE)

    if not attempted_any:
        await type_out_text(screen, random.choice(no_suitable_statements), font)
    await _apply_challenge_penalty(team, archetype.get("penalty"), screen, font)
    reset_x_offset()
    return False


def make_challenge_outcome(archetype_key):
    async def _outcome(team, stat_name, skill_name, screen, font):
        await resolve_procedural_challenge(team, archetype_key, screen, font)
    return _outcome


async def calculate_outcome_locked_portal(team, stat_name, skill_name, screen, font):
    await resolve_procedural_challenge(team, "LOCKED_PORTAL", screen, font)
    return None


async def calculate_goal_outcome_hack(member, screen, font):
    await type_out_text(screen, f"{member.name} steps up to hack into the console:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    diff = 0 + get_specialist_position_bonus(member)
    skill_check = member.stat_and_skill_check(roll, None, "Hacking", diff)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, "Hacking", None, diff), font, color)

    if skill_check:
        result_text = f"{member.name} gets access and downloads secrets (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill("Hacking", 5)
        result = True
    else:
        result_text = f"{member.name} could not break in."
        result = False

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

async def calculate_goal_outcome_explosives(member, screen, font):
    await type_out_text(screen, f"{member.name} steps up to place explosives at the mechanism:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    diff = 0 + get_specialist_position_bonus(member)
    skill_check = member.stat_and_skill_check(roll, None, "Explosives", diff)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, "Explosives", None, diff), font, color)

    if skill_check:
        result_text = f"{member.name} detonates a shaped charge and forces the vault open (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill("Explosives", 5)
        result = True
    else:
        result_text = f"{member.name} detonates a shaped charge but the mechanism remains secured."
        result = False

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

async def calculate_goal_outcome_cutter(member, screen, font):
    await type_out_text(screen, f"{member.name} begins to work on the controller with their cutter:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    cutter = member.get_item("cutter")
    cutter_bonus = (cutter.effect - 20) if cutter else 10
    diff = cutter_bonus + get_specialist_position_bonus(member)
    skill_check = member.stat_and_skill_check(roll, "coordination", None, diff)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, None, "coordination", diff), font, color)

    if skill_check:
        result_text = f"{member.name} cuts past the controller and forces the portal open (+10 mission points)."
        member.mission_points += 10
        result = True
    else:
        result_text = f"{member.name} tries cutting in, but the area remains unbreached."
        result = False

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

async def calculate_goal_outcome_negotiation(member, screen, font):
    await type_out_text(screen, f"{member.name} attempts to negotiate with the AI:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    diff = 10 + get_specialist_position_bonus(member)
    skill_check = member.skill_check(roll, "Negotiation", diff)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, "Negotiation", None, diff), font, color)

    if skill_check:
        result_text = f"{member.name} convinces the AI to cooperate and grant access (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill("Negotiation", 5)
        result = True
    else:
        result_text = f"{member.name} could not reach an agreement with the AI."
        result = False

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

async def calculate_goal_outcome_diplomacy(member, screen, font):
    await type_out_text(screen, f"{member.name} attempts a diplomatic approach with the AI:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    diff = 10 + get_specialist_position_bonus(member)
    skill_check = member.skill_check(roll, "Diplomacy", diff)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, "Diplomacy", None, diff), font, color)

    if skill_check:
        result_text = f"{member.name} establishes a diplomatic accord with the AI, gaining access (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill("Diplomacy", 5)
        result = True
    else:
        result_text = f"{member.name} could not establish terms the AI would accept."
        result = False

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

async def calculate_goal_outcome_espionage(member, screen, font):
    await type_out_text(screen, f"{member.name} tries to use their skill in espionage:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    diff = 10 + get_specialist_position_bonus(member)
    skill_check = member.stat_and_skill_check(roll, None, "Espionage", diff)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, "Espionage", None, diff), font, color)

    if skill_check:
        result_text = f"{member.name} succeeds in the operation (+10 mission points)."
        member.mission_points += 10
        result = True
    else:
        result_text = f"{member.name} fails to make any progress."
        result = False

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

async def calculate_outcome_pirate_vault(team, stat_name, skill_name, screen, font):
    global mission_failed

    mission_failed = True  # assume failure until a method succeeds

    if DEBUG:
        print("Trying hacking")
    member = determine_best_team_member(team, None, "Hacking")
    if member:
        mission_failed = not await calculate_goal_outcome_hack(member, screen, font)
        if DEBUG:
            print(f"{mission_failed}")

    if mission_failed:
        if DEBUG:
            print("Trying explosives")
        member = determine_best_team_member(team, None, "Explosives",)
        if member:
            mission_failed = not await calculate_goal_outcome_explosives(member, screen, font)
            print(f"{mission_failed}")

    if mission_failed:
        if DEBUG:
            print("Trying cutter")
        if team_has_item(team, "cutter"):
            member = next(m for m in team if m.has_item("cutter"))
            mission_failed = not await calculate_goal_outcome_cutter(member, screen, font)
            print(f"{mission_failed}")

    if mission_failed:
        await type_out_text(screen, "The mission has failed!", font)
    else:
        mission_failed = False
        await type_out_text(screen, "The Trilisk artifact is retrieved from the breached vault.\n Mission objective has been achieved!", font)

    return

async def calculate_outcome_officers_quarters_jalorith(team, stat_name, skill_name, screen, font):
    global mission_failed

    mission_failed = False
    if team_has_item(team, "pacifier"):
        captor = next((m for m in team if m and m.is_alive() and m.has_item("pacifier")), team[0] if team else None)
        if captor is not None:
            captor.mission_points += 15
        await type_out_text(
            screen,
            "Jalorith is incapacitated with a pacifier and taken alive for Space Force interrogation! (+15 bonus mission points)",
            font,
            GREEN,
        )
    else:
        await type_out_text(screen, "Jalorith has been defeated. The mission objective has been achieved!", font)
    return

async def calculate_outcome_officers_quarters_neutralize(team, stat_name, skill_name, screen, font):
    global mission_failed

    mission_failed = False
    await type_out_text(screen, "All the pirates have been neutralized. The mission objective has been achieved!", font)
    return

async def calculate_outcome_ai_core(team, stat_name, skill_name, screen, font):
    global mission_failed

    mission_failed = True  # assume failure until a method succeeds

    member = determine_best_team_member(team, None, "Negotiation")
    if member:
        mission_failed = not await calculate_goal_outcome_negotiation(member, screen, font)

    if mission_failed:
        member = determine_best_team_member(team, None, "Espionage")
        if member:
            mission_failed = not await calculate_goal_outcome_espionage(member, screen, font)

    if mission_failed:
        member = determine_best_team_member(team, None, "Diplomacy")
        if member:
            mission_failed = not await calculate_goal_outcome_diplomacy(member, screen, font)

    if mission_failed:
        await type_out_text(screen, "The mission has failed!", font)
    else:
        mission_failed = False
        await type_out_text(screen, "The AI core yields the secret information to the team.\nThe mission objective has been achieved!", font)

    return

async def calculate_outcome_hack_a_console(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} steps up to hack into the console:", font)
    else:
        await type_out_text(screen, random.choice(no_suitable_statements), font)
        result_text = "No one can access any data from here."
        await type_out_text(screen, result_text, font, WHITE)
        return

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    diff = 0 + get_specialist_position_bonus(member)
    skill_check = member.stat_and_skill_check(roll, stat_name, skill_name, diff)
    if skill_check:
        color = GREEN
    else: color = RED
    await type_out_text(screen, roll_string(roll, skill_name, stat_name, diff), font, color)

    if skill_check:
        result_text = f"{member.name} gets access and downloads secrets (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill(skill_name, 5)
        member.increase_stat(stat_name, 3)
    else:
        result_text = f"{member.name} could not discover anything useful."

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

async def empty_outcome(team, stat_name, skill_name, screen, font):
    return


async def calculate_outcome_derelict_toxic_air(team, stat_name, skill_name, screen, font):
    """Klackon derelict ship event: best team member rolls against Survival to counter toxic air,
    or on failure the team takes a 5% health and morale hit."""
    await type_out_text(screen, "The air on this ship is making the team fall ill.", font, WHITE)
    member = determine_best_team_member(team, stat_name, "Survival")
    if member and member.get_effective_skill_level("Survival", learning=False) > 0:
        diff = 0 + get_specialist_position_bonus(member)
        await type_out_text(screen, f"{member.name} attempts to counteract the atmospheric toxin:", font)
        check_passed = await standard_skill_check(member, screen, stat_name, "Survival", font, diff)
        if check_passed:
            await type_out_text(
                screen,
                f"{member.name} pinpoints the issue and administers a drug to counteract the effects.\n(+5 mission points)",
                font,
                GREEN,
            )
            member.mission_points += 5
            member.increase_skill("Survival", 2)
            reset_x_offset()
            return True
        else:
            await type_out_text(
                screen,
                f"{member.name} cannot identify a counteragent in time.",
                font,
                WHITE,
            )
    else:
        await type_out_text(screen, random.choice(no_suitable_statements), font)

    for m in team:
        if m and m.is_alive() and not m.is_robot():
            hp_loss = max(1, round(m.get_max_health() * 0.05))
            m.current_health = max(1, m.current_health - hp_loss)
            m.demoralize(5)
            m.morale = min(m.morale, m.health_pct())
    await type_out_text(
        screen,
        "The toxic air saps the crew's strength! (-5% health and -5 morale)",
        font,
        RED,
    )
    reset_x_offset()
    return False


async def calculate_outcome_derelict_warpchamber(team, stat_name, skill_name, screen, font):
    global mission_failed
    await calculate_outcome_pirate_vault(team, stat_name, skill_name, screen, font)
    if not mission_failed:
        await type_out_text(screen, "The Xeno-Relic is extracted from the warp containment core!", font, GREEN)


async def calculate_outcome_derelict_throneroom(team, stat_name, skill_name, screen, font):
    global mission_failed
    mission_failed = False
    await type_out_text(screen, "Broodmother Xylarx has been defeated. The mission objective has been achieved!", font)


async def calculate_outcome_derelict_biolab(team, stat_name, skill_name, screen, font):
    global mission_failed
    mission_failed = False
    await type_out_text(screen, "The Klackon bio-nest has been purged. The mission objective has been achieved!", font)


async def calculate_outcome_derelict_bridge(team, stat_name, skill_name, screen, font):
    global mission_failed
    mission_failed = True

    for skill in ("Hacking", "Ships Systems", "Navigation", "Artifact Analysis"):
        member = determine_best_team_member(team, "intelligence", skill)
        if member and member.has_skill(skill):
            await type_out_text(screen, f"{member.name} attempts to extract the flight core using {skill}:", font)
            diff = 10 + get_specialist_position_bonus(member)
            if await standard_skill_check(member, screen, "intelligence", skill, font, diff):
                member.mission_points += 10
                member.increase_skill(skill, 4)
                mission_failed = False
                break

    if mission_failed:
        await calculate_outcome_ai_core(team, stat_name, skill_name, screen, font)
    else:
        await type_out_text(screen, "The derelict's black-box flight core is secured.\nThe mission objective has been achieved!", font)


ROOM_ENTRY_TEXT = {
    # combat (pirates & derelict)
    "barracks": ("The team breaches a hatch and enters the pirate barracks.", "The barracks have been cleared."),
    "barracks1": ("The team steps into a deserted crew barracks strewn with chitin carapaces.", "The barracks have been cleared."),
    "barracks2": ("The team breaches a secondary troop berth converted into a Klackon nesting den.", "The nesting den has been cleared."),
    "guard room": ("The team pushes into a fortified guard room.", "The guard post is secure."),
    "checkpoint": ("The team approaches an internal security checkpoint.", "The checkpoint has been secured."),
    "training room": ("The team enters a sprawling combat training hall.", "The training room is clear."),
    "drone launch": ("The team steps into a drafty drone launch bay.", "The drone bay has been cleared."),
    "shipsweapons": ("The team enters the derelict's heavy weapons battery deck.", "The weapons deck is secure."),
    # tech (pirates & derelict)
    "radar tower": ("The team ascends into the radar observation tower.", "The radar tower is secure."),
    "war room": ("The team slips into a tactical war room lined with holomaps.", "The war room has been searched."),
    "environmental control": ("The team enters the environmental control hub.", "Environmental control is stabilized."),
    "artifact analysis": ("The team enters a chamber equipped to scan unknown artifacts.", "The analysis lab is clear."),
    "analysisbay": ("The team enters an alien specimen and artifact analysis bay.", "The analysis bay is clear."),
    "captainquarters": ("The team enters the former captain's quarters.", "The captain's quarters have been searched."),
    "engineering": ("The team enters main engineering, where damaged conduits hiss with plasma.", "Engineering has been secured."),
    "generator": ("The team steps into a cavernous auxiliary power generator chamber.", "The generator room is clear."),
    "navigation": ("The team enters a stellar navigation dome displaying dead star charts.", "The navigation dome is clear."),
    # medical (pirates & derelict)
    "medical bay": ("The team enters a bloodstained pirate medical facility.", "The medical bay has been cleared."),
    "medbay": ("The team enters an abandoned sickbay with overturned stasis beds.", "The medbay has been cleared."),
    "implant room": ("The team enters a surgical suite filled with implant rigs.", "The implant room is clear."),
    "implant": ("The team enters a cybernetic surgical bay with flickering diagnostic screens.", "The implant bay is clear."),
    "bioaugmentation": ("The team breaches a hatch into a bioaugmentation lab.", "Bioaugmentation has been cleared."),
    # supply (pirates & derelict)
    "armory": ("The team discovers a workroom stacked with weapons and ordinance.", "The armory has been searched."),
    "depot": ("The team enters a fuel and energy storage depot.", "The depot has been cleared."),
    "parts bay": ("The team steps into a bay lined with spare parts and machinery.", "The parts bay is clear."),
    "parts": ("The team enters a spare-parts warehouse stacked with salvaged hull plating.", "The parts bay is clear."),
    "storage": ("The team spots a cluttered storage room off the main passage.", "The storage room has been searched."),
    "fabrication": ("The team enters an industrial fabrication room.", "The fabrication bay is clear."),
    "workshop": ("The team enters a cluttered mechanical workshop.", "The workshop has been cleared."),
    "vehicle bay": ("The team enters a cavernous vehicle maintenance bay.", "The vehicle bay is secure."),
    "orechamber": ("The team enters a raw ore processing chamber hollowed out by mandibles.", "The ore chamber is clear."),
    "robotshop": ("The team enters a robotics maintenance shop littered with dismantled chassis.", "The robot shop is clear."),
    "suitroom": ("The team enters an EVA suit locker room.", "The suit room has been searched."),
    # corridor & prison (pirates & derelict)
    "corridor": ("The team travels through a narrow corridor.", "The corridor is clear."),
    "s-corridor": ("The team moves along a curved service corridor winding through the hull.", "The service corridor is clear."),
    "empty": ("The team crosses a stripped, depressurized hull compartment.", "The hull compartment is clear."),
    "quarters1": ("The team passes through abandoned crew quarters smelling of ozone and chitin.", "The crew quarters are clear."),
    "quarters2": ("The team searches dimly lit officer berths scored with claw marks.", "The officer berths are clear."),
    "shuttlebay": ("The team moves through a cavernous shuttle bay.", "The shuttle bay is secure."),
    "cargo lift": ("The team steps onto a heavy industrial cargo lift.", "The cargo lift area is clear."),
    "new chamber": ("The team passes into an unfinished chamber carved from rock.", "This chamber has been cleared."),
    "well": ("The team crosses a damp water extraction and storage room.", "The well room is clear."),
    "canteen": ("The team finds a colorful canteen with tables and a bar.", "The canteen has been cleared."),
    "game room": ("The team passes through a noisy pirate entertainment room.", "The game room is clear."),
    "smuggler's den": ("The team enters a dimly lit smuggler's lounge.", "The smuggler's den is clear."),
    "prison": ("The team discovers a grim detention block with holding cells.", "The prison block has been cleared."),
}

TAG_WEIGHTS_BY_OPTION = {
    "focus": {"corridor": 35, "combat": 30, "tech": 15, "medical": 15, "supply": 5},
    "flex": {"tech": 35, "supply": 25, "corridor": 15, "combat": 15, "medical": 10},
    "default": {"corridor": 25, "combat": 25, "tech": 20, "supply": 15, "medical": 15},
}


def build_procedural_mission_room_event(
    team,
    locations,
    all_items,
    last_room_name=None,
    supply_locker_state=None,
):
    """Build a procedural mission room Event using Pirate or Derelict room tags and MissionOrders options.

    Keeping usable item drops rare:
    - 'supply' rooms usually present LOCKED_PORTAL, HAZARD_LEAK, or INTEL_CONSOLE challenges.
    - SUPPLY_LOCKER (which rewards a usable unkeyed item) only triggers on a 20% roll in a
      supply room and at most once per mission when supply_locker_state is provided.
    """
    options = None
    if team and getattr(team[0], "mission", None):
        options = team[0].mission.get("options")
    weights_map = TAG_WEIGHTS_BY_OPTION.get(options, TAG_WEIGHTS_BY_OPTION["default"])

    # Group available non-goal rooms by tag (plus 'prison' under 'corridor' for CAPTIVE_CELL)
    rooms_by_tag = {"combat": [], "tech": [], "medical": [], "supply": [], "corridor": []}
    excluded_goal_rooms = (
        "entrance", "ai core", "officer's quarters", "vault",
        "throneroom", "warpchamber", "biolab", "bridge",
    )
    for name, loc in locations.items():
        if name == last_room_name or name in excluded_goal_rooms:
            continue
        tags = getattr(loc, "tags", ())
        if name == "prison":
            rooms_by_tag["corridor"].append(loc)
        else:
            for t in rooms_by_tag:
                if t in tags:
                    rooms_by_tag[t].append(loc)
                    break

    available_tags = [t for t, locs in rooms_by_tag.items() if locs]
    tag_weights = [weights_map.get(t, 15) for t in available_tags]
    chosen_tag = random.choices(available_tags, weights=tag_weights, k=1)[0]
    chosen_loc = random.choice(rooms_by_tag[chosen_tag])
    room_name = chosen_loc.name

    pre_desc, post_desc = ROOM_ENTRY_TEXT.get(
        room_name,
        (f"The team enters the {room_name}.", f"The {room_name} has been cleared."),
    )

    # Determine enemies and challenge archetype by room/tag
    archetype_key = None
    if room_name == "prison":
        num_enemies = random.choice([1, 2, 3])
        archetype_key = "CAPTIVE_CELL"
    elif chosen_tag == "combat":
        num_enemies = random.randint(2, 5)
        if room_name in ("checkpoint", "guard room") and random.random() < 0.5:
            archetype_key = random.choice(["SECURITY_GRID", "CAPTIVE_CELL"])
        elif random.random() < 0.35:
            archetype_key = "SECURITY_GRID"
    elif chosen_tag == "tech":
        num_enemies = random.choice([0, 1, 2])
        if room_name in ("environmental control", "engineering", "generator"):
            archetype_key = "HAZARD_LEAK"
        else:
            archetype_key = "INTEL_CONSOLE" if random.random() < 0.75 else "SECURITY_GRID"
    elif chosen_tag == "medical":
        num_enemies = random.choice([0, 1, 2])
        if room_name in ("implant room", "bioaugmentation", "implant"):
            archetype_key = "CYBER_IMPLANT_BAY"
        else:
            archetype_key = "MEDICAL_CACHE"
    elif chosen_tag == "supply":
        num_enemies = random.choice([0, 1, 2])
        already_used = bool(supply_locker_state and supply_locker_state.get("used"))
        if not already_used and random.random() < 0.20:
            archetype_key = "SUPPLY_LOCKER"
            if isinstance(supply_locker_state, dict):
                supply_locker_state["used"] = True
        else:
            archetype_key = random.choice(["LOCKED_PORTAL", "HAZARD_LEAK", "INTEL_CONSOLE"])
    else:  # corridor
        num_enemies = random.choice([0, 0, 2, 3])
        roll = random.random()
        if roll < 0.35:
            archetype_key = "LOCKED_PORTAL"
        elif roll < 0.55:
            archetype_key = "SECURITY_GRID"

    # For the 'defeat 20 enemies' objective (mission_index == 4), ensure steady hostile patrols
    mission_idx = (
        team[0].mission.get("mission_index")
        if team and getattr(team[0], "mission", None)
        else None
    )
    if mission_idx == 4 and num_enemies == 0 and random.random() < 0.65:
        num_enemies = random.randint(2, 4)

    is_derelict = (
        (team and getattr(team[0], "mission", None) and team[0].mission.get("theatre") == "derelict")
        or "throneroom" in locations
        or "biolab" in locations
    )
    toxic_air_used = bool(supply_locker_state and supply_locker_state.get("toxic_air_used"))
    if archetype_key is None and is_derelict and not toxic_air_used:
        outcome_fn = calculate_outcome_derelict_toxic_air
        if isinstance(supply_locker_state, dict):
            supply_locker_state["toxic_air_used"] = True
    else:
        outcome_fn = make_challenge_outcome(archetype_key) if archetype_key else empty_outcome
    return Event(
        pre_desc,
        post_desc,
        num_enemies,
        None,
        None,
        chosen_loc,
        outcome_fn,
        all_items,
        name=room_name,
    )


async def go_mission(team_data, team_name="Debug Team", loop=1) :
    global max_height
    global locations
    global mission_failed
    global rooms_to_goal

    mission_failed = False
    max_height = SCREEN_HEIGHT - CREDITS_BAR_HEIGHT
    reset_text_offsets()

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Mission")
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)
    LOCATION_FONT = pygame.font.Font(font_path, 18)
    SMALL_FONT = pygame.font.Font(font_path, 12)
    EXIT_RECT = pygame.Rect(1330, TOP_BAR_Y, 105, 25)
    stage = 6

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 5)
    team = [Character.from_dict(data) for data in team_data]
    for member in team:
        member.team = team
    # Hacking icon sizes-- redo this
    for member in team:
        member.portrait = pygame.transform.scale(member.portrait, (60, 70))
        for item in member.equipment:
            item.icon = pygame.transform.scale(item.icon, (40, 40))

    # Load sounds
    play_background_music("music/track3.mp3", pygame)

    theatre = (
        (team[0].mission.get("theatre") if team and getattr(team[0], "mission", None) else None)
        or get_theatre_for_loop(loop)
    )
    add_team_mission_param(team, "theatre", theatre)
    add_team_mission_param(team, "loop", loop)
    add_team_mission_param(team, "enemies_defeated", 0)

    # Load locations and attributes for current theatre
    if theatre == "derelict":
        locations = load_derelict_locations()
    else:
        locations = load_pirate_locations()
    all_items = load_items_battle()

    if theatre == "derelict":
        goal_event = [
            Event(
                "The team breaches a sealed bulkhead and enters the derelict's warp chamber.",
                "The warp containment vault must be breached to recover the Xeno-Relic.",
                5, "Intelligence", "Hacking", locations["warpchamber"],
                calculate_outcome_derelict_warpchamber,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team breaches a chitin-encrusted hatch into the hive throne room!",
                "Broodmother Xylarx is neutralized. The mission has been completed!",
                6, None, None, locations["throneroom"],
                calculate_outcome_derelict_throneroom,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team breaches a hatch and enters the overgrown derelict biolab!",
                "The Klackon bio-nest has been purged. The mission is a success!",
                5, None, None, locations["biolab"],
                calculate_outcome_derelict_biolab,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team reaches the dark command bridge of the derelict vessel!",
                "The team must extract the black-box flight core to succeed.",
                5, None, None, locations["bridge"],
                calculate_outcome_derelict_bridge,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team sweeps a Klackon staging chamber aboard the derelict vessel!",
                "The Klackon swarm in this sector has been neutralized.",
                5, None, None, locations["guard room"],
                empty_outcome,
                all_items,
                is_goal=True,
            ),
        ]
    else:
        goal_event = [
            Event(
                "The team breaches a hatch and discovers a vault room beyond.",
                "The vault must be breached to obtain the mission objective.",
                5, "Intelligence", "Hacking", locations["vault"],
                calculate_outcome_pirate_vault,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team breaches a hatch and discovers the officer's quarters!",
                "Jalorith is neutralized. The mission has been completed!",
                6, None, None, locations["officer's quarters"],
                calculate_outcome_officers_quarters_jalorith,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team breaches a hatch and discovers the officer's quarters!",
                "Pirate officers have been neutralized. The mission is a success!",
                5, None, None, locations["officer's quarters"],
                calculate_outcome_officers_quarters_neutralize,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team breaches a hatch and discovers the ai core room!",
                "The team must obtain secrets held by the AI core to succeed.",
                5, None, None, locations["ai core"],
                calculate_outcome_ai_core,
                all_items,
                is_goal=True,
            ),
            Event(
                "The team storms a heavily guarded pirate barracks!",
                "The pirate patrol has been neutralized.",
                5, None, None, locations["guard room"],
                empty_outcome,
                all_items,
                is_goal=True,
            ),
        ]

    rando_atmosphere_strings = [
        " the scent of oil and burnt metal fills the air, mingling with the faint aroma of alien spices.",
        " dim, flickering lights cast long shadows, making the base feel even more menacing.",
        " the sound of distant shouting and clanking echoes through the corridors.",
        " holographic wanted posters line the walls, some bearing unsettling resemblances to the team.",
        " the constant hum of the reactor below the base creates a faint vibration underfoot.",
        " the team feels a mix of thrill and unease as rowdy pirates share tales of plunder nearby.",
        " the background hum of life support circulating air breaks the tense silence.",
        " the base's patchwork construction gives the impression it could collapse at any moment.",
        f" {team[random.randint(0, len(team) - 1)].name} sees something in the shadows, then determines nothing is there.",
        " the team debates whether the treasure map on the wall is genuine or a trap.",
        " the glow of a failing light bar paints the area in eerie colors.",
        " a distant intercom speaker emits a song of betrayal and revenge, setting everyone on edge.",
        " the distant sound of laughter echoes through an air duct.",
        f" {team[random.randint(0, len(team) - 1)].name} accidentally bumps into something, making too much noise.",
        " the team notices strange graffiti in a language none of them can decipher.",
        " a faint smell of alien flora wafts in from the base’s vent system, oddly calming amidst the chaos.",
        " a gang of pirates loudly debates something in the distance.",
        " the walls of the base are lined with crates of smuggled goods, their origins a mystery.",
        f" {team[random.randint(0, len(team) - 1)].name} hears an unidentifiable language echoing in the distance.",
        " the base’s dim atmosphere is momentarily broken by a sharp alarm, leaving the team on edge.",
    ]

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage4.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))

    hour = 1
    voyage_complete = False
    # Display the hour
    day_text = DEFAULT_FONT.render(f"HOUR {hour}", True, CYAN)
    screen.blit(day_text, (40, 10))
    ship_text = DEFAULT_FONT.render("The team arrives at the mission point", True, CYAN)
    screen.blit(ship_text, (120, 10))
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    if theatre == "derelict":
        intro_text = "The team docks with the derelict vessel at the mission point..."
    else:
        intro_text = "The team arrives on planet at the mission point..."
    await type_out_text(screen, intro_text, DEFAULT_FONT)

    mission_index = team[0].mission["mission_index"]
    goals_list = get_mission_goals_for_theatre(theatre)
    intro_text = goals_list[mission_index][0]
    await type_out_text(screen, intro_text, DEFAULT_FONT)
    await share_spare_weapons(team, screen, DEFAULT_FONT)
    intro_text = "Click to proceed."
    await type_out_text(screen, intro_text, DEFAULT_FONT)

    location = locations.get("entrance") or locations.get("shuttlebay") or next(iter(locations.values()))
    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
    mission_options = team[0].mission.get("options") if team and getattr(team[0], "mission", None) else None
    if mission_options == "focus":
        rooms_to_goal = random.randint(4, 5)
    elif mission_options == "flex":
        rooms_to_goal = random.randint(6, 8)
    else:
        rooms_to_goal = 5
    last_repeatable_event_name = None
    supply_locker_state = {"used": False}

    if team is None:
        if DEBUG:
            print("Team is None")

    # Event Loop
    running = True
    waiting = True
    while running:
        for event in pygame.event.get():
            if team_dead(team) or mission_failed:
                if team_dead(team):
                    await mission_failure(screen, DEFAULT_FONT)
                running = False
                stage = 999  # sentinel: will return 1000 → StageController restarts
                break

            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False
                else:
                    play_positive_click()
                    waiting = False
                    await update_screen(screen, background_image, hour, DEFAULT_FONT)
                    if not voyage_complete:
                        rando_text = ""
                        if rando_atmosphere_strings and random.randint(0, 100) < 30:
                            rando_index = random.randint(0, len(rando_atmosphere_strings) - 1)
                            rando_text = rando_atmosphere_strings.pop(rando_index)
                        await type_out_text(screen, "The team continues..." + rando_text, DEFAULT_FONT)
                    else:
                        running = False
                        waiting = True

        # Move to next event
        if not waiting:
            if mission_index != 4 and rooms_to_goal <= 0:
                # goal event for mission
                event = goal_event[mission_index]
                location = event.context.location
                draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                pygame.event.clear()   # discard clicks buffered during the battle/event
                hour += 1
                voyage_complete = True
                if not mission_failed:
                    team_mission_success(team)
                elif not team_dead(team):
                    play_defeat_sound()
            else:
                event = build_procedural_mission_room_event(
                    team,
                    locations,
                    all_items,
                    last_room_name=last_repeatable_event_name,
                    supply_locker_state=supply_locker_state,
                )
                last_repeatable_event_name = event.name
                location = event.context.location
                draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                pygame.event.clear()   # discard clicks buffered during the battle/event
                rooms_to_goal -= 1
                hour += 1
                if (
                    mission_index == 4
                    and not team_dead(team)
                    and not mission_failed
                    and team[0].mission.get("enemies_defeated", 0) >= 20
                ):
                    await type_out_text(
                        screen,
                        "All 20 hostiles have been neutralized! The mission objective has been achieved!",
                        DEFAULT_FONT,
                        GREEN,
                    )
                    voyage_complete = True
                    mission_failed = False
                    team_mission_success(team)
            waiting = True

        # Update the display
        screen.blit(EXIT_TEXT, EXIT_RECT)
        pygame.display.flip()
        await asyncio.sleep(0)

    # Save characters upon exit (only on clean exit, not team death/quit)
    if stage not in (999, 1000):
        team_data = save_team_named(team_name, loop, 6, team)
    else:
        team_data = None

    return stage + 1, team_data

async def main():
    print("Starting Stage: Mission")
    team_data = mission(None)

if __name__ == "__main__":
    main()

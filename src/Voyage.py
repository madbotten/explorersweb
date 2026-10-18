import pygame
import os
import random
import pickle
import asyncio
import sys

from Character import Character
from DrawUtils import DrawingContext
from Location import *
from Item import *
from Mission import calculate_outcome_hack_a_console
from Utils import *
from Event import *
from TypeText import *
from Interaction import Interaction, PRIVATE, PUBLIC, PERSONAL, PROFESSIONAL
from constants import TOP_BAR_Y, DEBUG

# Screen settings
TEXT_AREA_WIDTH = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 8  # Adjust for 8 characters, reserving space for credits
BASE_TEXT_X_OFFSET = 50

no_suitable_statements = [
    "However, no one on the team is a suitable instructor.",
    "No one has any valuable skills to share.",
    "The team doesn't really know what they are doing.",
    "The team lacks someone capable of effective instruction.",
    "There isn't anyone with the expertise needed to guide others.",
    "No one on the team possesses the necessary teaching skills.",
    "The team is missing a member who can effectively pass on knowledge.",
    "None of the team members are experienced enough to instruct.",
    "There’s no one on the team who feels confident enough to teach.",
    "No one here has the ability to instruct others properly.",
    "The team doesn't have someone with skills to share on this subject.",
    "None of the members are equipped to share their expertise."
]

teaches_statements = [
    "shares many valuable insights with the team.",
    "provides excellent instruction.",
    "is able to help everyone master some concepts.",
    "delivers practical knowledge to the group.",
    "breaks down complex topics into simple concepts for the team.",
    "helps teammates overcome obstacles with clear guidance.",
    "instills confidence in the group through effective teaching.",
    "shares a wealth of experience to support everyone's growth.",
    "leads the team with clear and concise instruction.",
    "bridges knowledge gaps with insightful explanations.",
    "demonstrates a clear understanding of the material.",
    "guides everyone through difficult tasks step by step.",
    "empowers the team with actionable knowledge.",
]

teacher_responds_statements = [
    "responds by offering to train teammates:",
    "steps up to show some pointers:",
    "convinces everyone to listen up and learn something:",
    "offers to walk everyone through the process:",
    "decides to take the lead in teaching some key points:",
    "steps forward to share knowledge with the team:",
    "volunteers to provide a learning session:",
    "proposes a quick training to get everyone on the same page:",
    "initiates a hands-on learning session for the group:",
    "takes it upon themselves to demonstrate the right approach:",
    "actively engages with the team to pass on their expertise:",
    "encourages the team to follow along and learn something new:",
    "gets the team together for an impromptu training session:",
]

train_fail_statements = [
    "tries to teach the team, but only confuses them.",
    "provides instruction, but little of it gets through.",
    "fails to keep everyone's focus during the session.",
    "ends up leaving the team more confused than before.",
    "fails to clarify the topic effectively for everyone.",
    "tries to explain, but the message gets lost in translation.",
    "provides unclear examples that confuse the team further.",
    "cannot maintain the team’s attention long enough to teach.",
    "loses the group’s interest halfway through the session.",
    "ends up creating more questions than answers.",
    "struggles to deliver the content in a way that sticks.",
    "cannot simplify the concepts enough for everyone to follow.",
    "tries hard but fails to make the material understandable.",
]

no_suitable_team_member_statements = [
  "No suitable team members found to address the event.",
  "No one has the skill to prevent the fire from spreading in the area.",
  "No one responds in time.",
]

global locations
_fusion_reactor_failed = False

async def update_screen(surface, background, day, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"DAY {day}", True, CYAN)
    surface.blit(day_text, (40, TOP_BAR_Y))
    ship_text = font.render("The voyage of Knacknarpia to mission point", True, CYAN)
    surface.blit(ship_text, (140, TOP_BAR_Y))
    reset_text_offsets()

async def calculate_outcome_mysterious_sensor_signal(team, stat_name, skill_name, screen, font):
    # Determine the best team member to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by examining the sensor data:", font)
    else:
        await type_out_text(screen, "No suitable team members found to address the event.", font)
        await type_out_text(screen, "The Knacknarpia flies through a debris field due to a lack of warning.\nThe crew sustains minor injuries.", font)
        for member in team:
            if member:
                member.hurt(10, "impact")
        return

    # Run a skill check
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} determines that a course correction is needed to avoid interstellar debris.\n "
        member.increase_skill(skill_name, 3)
        await type_out_text(screen, result_text, font)
    else:
        result_text = f"{member.name} fails to understand the problem.\nKnacknarpia flies through a debris field. Team sustains minor injuries."
        await type_out_text(screen, result_text, font)
        for member in team:
            if member:
                member.hurt(5, "impact")
        return

    reset_x_offset()
    # Compound event
    return Event(
        "An unexpected debris field blocks the Knacknarpia.",
        "The debris field is passed.",
        0,
        "coordination", "Piloting", locations["bridge"],
        calculate_outcome_avoid_debris, None
    )

async def calculate_outcome_training(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} {random.choice(teacher_responds_statements)}", font)
    else:
        await type_out_text(screen, random.choice(no_suitable_statements), font)
        return

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    modifier = round(member.get_effective_skill_level("Instruction") / 2)
    skill_check = member.skill_check(roll, skill_name, modifier)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, skill_name, stat_name, modifier), font, color)

    if skill_check:
        result_text = f"{member.name} {random.choice(teaches_statements)}\n(Mission points + 1)"
        member.mission_points += 1
        for member in team:
          member.increase_skill(skill_name, 2)
          member.encourage(1)
    else:
        result_text = f"{member.name} {random.choice(train_fail_statements)}\n "

    await type_out_text(screen, result_text, font, WHITE)

async def calculate_outcome_rogue_maintenance_bot(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by remote shutdown of the bot:", font)
    else:
        await type_out_text(screen, "No suitable team members found to shutdown rogue machine.", font)
        await type_out_text(screen, "The Knacknarpia's power systems are damaged. The journey will take longer.", font)
        for member in team:
            if member:
                 member.demoralize(5)
        return

    # Simulate a skill check
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, 0)

    if check_passed:
        result_text = f"{member.name} makes a rapid code correction. The crew is safe.\nTheir robotics skill increases."
        member.increase_skill(skill_name, 3)
    else:
        result_text = f"{member.name} could not stop the robot in time.\nThe ship sustains damage."
        for member in team:
            if member:
                 member.demoralize(5)

    await type_out_text(screen, result_text, font, WHITE)

async def calculate_outcome_avoid_debris(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by rapid change of course:", font)
    else:
        await type_out_text(screen, "No suitable team members found to implement emergency course change.", font)
        await type_out_text(screen, "The Knacknarpia flies through a debris field due to a lack of warning. The crew sustains minor injuries.", font)
        for member in team:
            if member:
                 member.hurt(10, "impact")
        return

    # Simulate a skill check
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} makes a rapid course correction. The crew is safe.\nTheir piloting skill increases."
        member.increase_skill(skill_name, 3)
        member.encourage(1)
    else:
        result_text = f"{member.name} changed course but threw the crew around.\nTeam sustains minor injuries."
        for member in team:
            if member:
                 member.hurt(5, "impact")

    await type_out_text(screen, result_text, font, WHITE)

async def calculate_outcome_alien_signal(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} analyzes the mysterious signal:", font)
    else:
        await type_out_text(screen, "No suitable team members found to decode it.\nThe message will be turned in when the crew returns home.", font)
        return

    # Simulate a skill check
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} decodes the message, learning the location of an alien colony. (+20 mission points)\nTheir skill increases."
        member.mission_points += 20
        member.increase_skill(skill_name, 5)
        member.encourage(5)
    else:
        result_text = f"{member.name} could not decipher the message.\nIt will be stored for analysis upon return home."
        member.demoralize(2)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

async def calculate_outcome_ship_argument(team, stat_name, skill_name, screen, font):
    modifier = 0
    for member in team:
        if member.is_combative_personality():
            modifier -= 10

    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by intervening:", font)
    else:
        await type_out_text(screen, "No suitable team members found to address the event.", font)
        result_text = "The crew begins to brawl. The crew sustains minor injuries before they lose interest."
        await type_out_text(screen, result_text, font, WHITE)
        for member in team:
            if member:
                member.hurt(10, "impact")
                member.demoralize(5)
        return

    # Simulate a skill check
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, modifier)

    if check_passed:
        result_text = f"{member.name} talks the fight down, mending the disagreement while preserving egos.\nTheir leadership has been strengthened."
        member.increase_stat(stat_name, 3)
        member.increase_skill(skill_name, 3)
        member.encourage(5)
    else:
        result_text = f"{member.name} could not stop them in time. Team sustains very minor injuries after a brawl.\nThe team loses respect for their leader."
        for member in team:
            if member:
                member.hurt(10, "impact")
                member.demoralize(3)
        member.decrease_skill(skill_name, 3)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

async def calculate_outcome_ship_fire(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by activating a fire suppression system that was somehow left off:", font)
    else:
        await type_out_text(screen, random.choice(no_suitable_team_member_statements), font)
        result_text = "Some of the crew's items have been destroyed."
        if team_has_item(team, "techbot"):
            result_text = "Some of the crew's items were damaged. The techbot was able to repair them."
        else:
            for i in range(0,2):
                member = random.choice(team)
                if member and len(member.equipment) > 0:
                    member.equipment.remove(random.choice(member.equipment))
        await type_out_text(screen, result_text, font, WHITE)
        return

    # Simulate a skill check
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} stops the fire quickly.\nTheir skill has been strengthened."
        member.increase_skill(skill_name, 5)
        member.encourage(1)
    else:
        result_text = f"{member.name} could not stop the fire in time.\nOne of the crew's items have been destroyed."
        if team_has_item(team, "techbot"):
            result_text = f"{member.name} could not stop the fire in time.\nOne of the crew's items were damaged, but the techbot was able to repair them."
        else:
            member = random.choice(team)
            if member and len(member.equipment) > 0:
                member.equipment.remove(random.choice(member.equipment))
                member.demoralize(3)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

async def calculate_outcome_fusion_reactor(team, stat_name, skill_name, screen, font):
    """A contaminated fusion reactor requires a physicist to stabilise it.

    Success: crew member gains +5 Physics knowledge and 3 mission points.
    Failure: voyage takes longer (max_events_in_voyage += 2) and
             the whole team loses 5 mission points.
    """
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} rushes to the reactor bay and begins containment procedures:", font)
    else:
        await type_out_text(screen, "No one on the team has the physics knowledge to clean the reactor.", font)
        result_text = (
            "Without a physicist aboard, the contamination slows the reactors.\n"
            "The crew is forced onto a longer emergency route. (-5 mission points each)"
        )
        await type_out_text(screen, result_text, font, RED)
        for m in team:
            if m:
                m.mission_points = max(0, m.mission_points - 5)
        return

    # Simulate a skill check — physics is hard, apply a penalty
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        result_text = (
            f"{member.name} stabilises the reactor and flushes the contamination safely.\n"
            f"Their Physics knowledge deepens. (+5 Physics, +3 mission points)"
        )
        member.increase_skill(skill_name, 5)
        member.mission_points += 3
        member.encourage(2)
    else:
        result_text = (
            f"{member.name} slows the contamination but cannot fully contain it.\n"
            f"The Knacknarpia must take a longer, safer route. (-5 mission points each)"
        )
        for m in team:
            if m:
                m.mission_points = max(0, m.mission_points - 5)
        # Signal to the voyage loop that it should extend the voyage
        # by returning a sentinel value via a module-level flag
        global _fusion_reactor_failed
        _fusion_reactor_failed = True

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

async def calculate_outcome_plasma_torpedo(team, stat_name, skill_name, screen, font):
    """A plasma torpedo in the magazine has become unstable and needs disarming.

    Success: crew member gains +5 Explosives skill, +3 mission points;
             every team member gains 2 courage.
    Failure: every team member loses 3 courage and 5 mission points.
    """
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} races to the magazine and begins disarming the torpedo:", font)
    else:
        await type_out_text(screen, "No one on the team has the explosives knowledge to disarm it.", font)
        result_text = (
            "With no one able to defuse the torpedo, the crew can only watch helplessly.\n"
            "The torpedo is jettisoned but the near-miss shakes the team. (-5 mission points, -3 courage each)"
        )
        await type_out_text(screen, result_text, font, RED)
        for m in team:
            if m:
                m.mission_points = max(0, m.mission_points - 5)
                m.decrease_stat("courage", 3)
        return

    # Disarming a live plasma torpedo is extremely dangerous — stiff penalty
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -15)

    if check_passed:
        result_text = (
            f"{member.name} cuts the right conduit and the torpedo goes cold. Crisis averted.\n"
            f"The crew's confidence soars. (+5 Explosives, +3 mission points, +2 courage each)"
        )
        member.increase_skill(skill_name, 5)
        member.mission_points += 3
        for m in team:
            if m:
                m.increase_stat("courage", 2)
        member.encourage(3)
    else:
        result_text = (
            f"{member.name} cannot fully disarm it — the torpedo is ejected into space before it detonates.\n"
            f"The close call rattles the entire crew. (-5 mission points, -3 courage each)"
        )
        for m in team:
            if m:
                m.mission_points = max(0, m.mission_points - 5)
                m.decrease_stat("courage", 3)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

async def empty_outcome(team, stat_name, skill_name, screen, font):
    return

# Crafting events — one per skill
async def calculate_outcome_weaponsmithing(team, stat_name, skill_name, screen, font):
    """A skilled team member tries to upgrade the class of a weapon."""
    all_items = load_items()
    # Collect all weapons (not already S) owned by any non-robot team member
    candidates = [
        (member, item)
        for member in team if not member.is_robot()
        for item in member.equipment
        if item.type == "weapon" and item_class(item.name) != "S"
    ]
    if not candidates:
        await type_out_text(screen, "The team has no weapons that can be improved further.", font)
        return

    member = determine_best_team_member(team, stat_name, skill_name)
    if not member:
        await type_out_text(screen, "No one on the team has Weaponsmithing skill to attempt an upgrade.", font)
        return

    # Pick the highest-effect weapon on the team as the target
    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    await type_out_text(screen, f"{member.name} sets to work in the engineering bay, attempting to upgrade {owner.name}'s {target_item.name}:", font)

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(screen, f"Success! The weapon has been upgraded to {upgraded.name}.", font, GREEN)
            await type_out_text(screen, f"{member.name}'s Weaponsmithing skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(screen, f"{member.name} worked diligently, but the weapon is already at its peak quality.\nThe weapon is unchanged.", font)
    else:
        await type_out_text(screen, f"{member.name} worked hard but couldn't achieve the desired improvement.\nThe weapon is unchanged.", font, RED)

async def calculate_outcome_armorsmithing(team, stat_name, skill_name, screen, font):
    """A skilled team member tries to upgrade the class of an armor item."""
    all_items = load_items()
    candidates = [
        (member, item)
        for member in team if not member.is_robot()
        for item in member.equipment
        if item.type == "armor" and item_class(item.name) != "S"
    ]
    if not candidates:
        await type_out_text(screen, "The team has no armor that can be improved further.", font)
        return

    member = determine_best_team_member(team, stat_name, skill_name)
    if not member:
        await type_out_text(screen, "No one on the team has Armorsmithing skill to attempt an upgrade.", font)
        return

    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    await type_out_text(screen, f"{member.name} carefully examines {owner.name}'s {target_item.name} and begins reworking it:", font)

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(screen, f"Success! The armor has been upgraded to {upgraded.name}.\n{member.name}'s Armorsmithing skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(screen, f"{member.name} worked carefully, but the armor is already peak quality.\nThe armor is unchanged.", font)
    else:
        await type_out_text(screen, f"{member.name} gave it their best effort but couldn't achieve an improvement.\nThe armor is unchanged.", font, RED)

async def calculate_outcome_tinkering(team, stat_name, skill_name, screen, font):
    """A skilled team member tries to upgrade the class of a misc item."""
    all_items = load_items()
    candidates = [
        (member, item)
        for member in team if not member.is_robot()
        for item in member.equipment
        if item.type == "misc" and item_class(item.name) != "S"
    ]
    if not candidates:
        await type_out_text(screen, "The team has no misc items that can be tinkered with further.", font)
        return

    member = determine_best_team_member(team, stat_name, skill_name)
    if not member:
        await type_out_text(screen, "No one on the team has Tinkering skill to attempt an upgrade.", font)
        return

    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    await type_out_text(screen, f"{member.name} pulls out tools and starts tinkering with {owner.name}'s {target_item.name}:", font)

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(screen, f"Success! The item has been upgraded to {upgraded.name}.\n{member.name}'s Tinkering skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(screen, f"{member.name} couldn't find a way to improve it further — the item is already at peak quality.\nThe item is unchanged.", font)
    else:
        await type_out_text(screen, f"{member.name} tinkered away but couldn't figure out the right approach.\nThe item is unchanged.", font, RED)

def _interaction_reaction_string(success: bool, score: int, target_name: str) -> str:
    """Return a UI string describing how the target felt about the interaction."""
    if success:
        if score >= 90:
            return f"{target_name} absolutely loved it."
        elif score >= 50:
            return f"{target_name} liked it."
        else:
            return f"{target_name} accepted it without complaint."
    else:
        if score <= -90:
            return f"{target_name} absolutely hated it."
        elif score <= -50:
            return f"{target_name} disliked it."
        else:
            return f"{target_name} was indifferent."

async def _run_interaction(team, screen, font, setting_type, privacy_level):
    """Core logic shared by all four interaction event outcomes."""
    non_robots = [m for m in team if not m.is_robot()]
    if len(non_robots) < 2:
        await type_out_text(screen, "The crew keeps to themselves.", font)
        return

    initiator = random.choice(non_robots)
    candidates = [m for m in team if m is not initiator]
    if not candidates:
        return
    target = random.choice(candidates)

    # Build observer list for PUBLIC interactions (0-2 random bystanders).
    if privacy_level == PUBLIC:
        bystanders = [m for m in team if m is not initiator and m is not target]
        num_observers = random.randint(0, min(2, len(bystanders)))
        observer_list = random.sample(bystanders, num_observers)
    else:
        observer_list = []

    result = Interaction.resolve(
        initiator, target,
        observer_list=observer_list,
        setting_type=setting_type,
        privacy_level=privacy_level,
    )

    await type_out_text(screen, result.sentence, font, WHITE)
    emit_character_image_at_text_offset(initiator, screen)

    liked_by_score = target.interaction_liked_by.get(result.interaction_type, 0)
    reaction = _interaction_reaction_string(result.success, liked_by_score, target.name)
    color = GREEN if result.success else RED
    await type_out_text(screen, reaction, font, color)

    if observer_list:
        names = ", ".join(m.name for m in observer_list)
        await type_out_text(screen, f"Witnessed by: {names}.", font, CYAN)
    else:
        await type_out_text(screen, "The interaction went unobserved.", font, CYAN)

    # Blank line to push text cursor past the portrait before "Click to continue".
    await type_out_text(screen, " ", font)

    # --- Fight escalation (Step 5) ---
    if result.fight_triggered:
        await type_out_text(
            screen,
            f"{target.name} is furious and starts a fight with {initiator.name}!",
            font, RED,
        )

        # Find highest-leadership non-combatant to mediate.
        eligible = [
            m for m in team
            if m is not initiator and m is not target and not m.is_robot()
        ]
        mediator = max(eligible, key=lambda m: m.stats.get("leadership", 0)) if eligible else None

        if mediator:
            await type_out_text(screen, f"{mediator.name} steps in to break it up:", font)
            check_passed = await standard_skill_check(
                mediator, screen, "leadership", "Social Engineering", font, 0
            )
            if check_passed:
                await type_out_text(
                    screen,
                    f"{mediator.name} manages to calm things down. Their leadership is strengthened.",
                    font, GREEN,
                )
                mediator.increase_stat("leadership", 3)
                mediator.increase_skill("Social Engineering", 3)
                mediator.encourage(5)
            else:
                await type_out_text(
                    screen,
                    f"{mediator.name} cannot stop them. The fight breaks out! Both sides take minor injuries.",
                    font, RED,
                )
                initiator.hurt(8, "impact")
                target.hurt(8, "impact")
                for m in team:
                    m.demoralize(3)
        else:
            await type_out_text(
                screen,
                "No one steps in. The brawl breaks out! Both sides take injuries.",
                font, RED,
            )
            initiator.hurt(12, "impact")
            target.hurt(12, "impact")
            for m in team:
                m.demoralize(5)

async def calculate_outcome_interaction_private_professional(team, stat_name, skill_name, screen, font):
    """PRIVATE PROFESSIONAL: a quiet work talk in crew quarters."""
    await _run_interaction(team, screen, font, PROFESSIONAL, PRIVATE)

async def calculate_outcome_interaction_public_professional(team, stat_name, skill_name, screen, font):
    """PUBLIC PROFESSIONAL: an open exchange on the bridge."""
    await _run_interaction(team, screen, font, PROFESSIONAL, PUBLIC)

async def calculate_outcome_interaction_private_personal(team, stat_name, skill_name, screen, font):
    """PRIVATE PERSONAL: a personal conversation behind closed doors."""
    await _run_interaction(team, screen, font, PERSONAL, PRIVATE)

async def calculate_outcome_interaction_public_personal(team, stat_name, skill_name, screen, font):
    """PUBLIC PERSONAL: a candid exchange in the mess hall."""
    await _run_interaction(team, screen, font, PERSONAL, PUBLIC)

async def calculate_outcome_inspirational_speech(team, stat_name, skill_name, screen, font):
    """Step 6: The highest-leadership non-robot addresses the crew before departure.

    Success: every non-robot crew member gains 5-20 relationship points with
             every other crew member, and +5 morale.
    Failure: nothing happens.
    """
    non_robots = [m for m in team if not m.is_robot()]
    if not non_robots:
        await type_out_text(screen, "There is no one suitable to address the crew.", font)
        return

    leader = max(non_robots, key=lambda m: m.stats.get("leadership", 0))
    await type_out_text(screen, f"{leader.name} addresses the crew before departure:", font)

    check_passed = await standard_skill_check(leader, screen, "leadership", "Instruction", font, 0)

    if check_passed:
        boost = random.randint(5, 20)
        await type_out_text(
            screen,
            f"{leader.name}'s words resonate with the crew.\n"
            f"The team feels inspired to work together toward a common goal.\n"
            f"(Relationships +{boost}, Morale +5)",
            font, GREEN,
        )
        for member in non_robots:
            member.encourage(5)
            for other in non_robots:
                if other is not member:
                    member.adjust_relationship(other.name, boost)
    else:
        await type_out_text(
            screen,
            f"{leader.name}'s words fall flat. The crew remains unmoved.",
            font, RED,
        )

async def calculate_outcome_out_of_oreos(team, stat_name, skill_name, screen, font):
    """Required outbound event: Supply Logistics check to avert an Oreo shortage.

    Pass → supplies properly managed, no penalty.
    Fail → all non-robot crew are demoralized by 5.
    """
    member = determine_best_team_member(team, None, "Supply Logistics")
    if member:
        await type_out_text(screen, f"{member.name} checks the supply manifest...", font)
        check_passed = await standard_skill_check(member, screen, None, "Supply Logistics", font, 0)
        if check_passed:
            await type_out_text(
                screen,
                f"Thanks to {member.name}'s careful rationing, Oreo supplies hold.\nCrisis averted.",
                font, GREEN,
            )
        else:
            await type_out_text(
                screen,
                "The Oreo supply has been exhausted.\nMorale suffers.",
                font, RED,
            )
            for m in team:
                if not m.is_robot():
                    m.demoralize(5)
        # Blank line to push text cursor past the portrait before "Click to proceed."
        await type_out_text(screen, " ", font)
    else:
        await type_out_text(
            screen,
            "With no one skilled in Supply Logistics, the Oreo shortage hits the crew hard.",
            font, RED,
        )
        for m in team:
            if not m.is_robot():
                m.demoralize(5)


async def voyage(team_data, team_name="Debug Team", loop=1) :
    global max_height
    global locations

    reset_text_offsets()
    max_height = SCREEN_HEIGHT - CREDITS_BAR_HEIGHT

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Voyage")

    drawContext = DrawingContext(screen)
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)
    LOCATION_FONT = pygame.font.Font(font_path, 18)
    SMALL_FONT = pygame.font.Font(font_path, 12)
    EXIT_RECT = pygame.Rect(1330, TOP_BAR_Y, 105, 25)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 3)
    team = [Character.from_dict(data) for data in team_data]
    for character in team:
        character.team = team

    # Resize portraits to fit into a small area for each character
    for character in team:
        if DEBUG:
            print(character.name)
        character.portrait = pygame.transform.scale(character.portrait, (70, 80))

    # Load and play background music
    play_background_music("music/track3.mp3", pygame)

    # Load locations and attributes
    locations = load_ship_locations()
    all_items = load_items_battle()

    # pre_description,
    # post_description,
    # num_enemies, stat_name, skill_name,location,
    # calculate_outcome,
    # all_items
    repeatable_events = [
        # Interaction events — four setting/privacy combinations
        Event(
            "A crew member pulls a teammate aside for a private work discussion.",
            None,
            0, None, None, locations["crew quarters"],
            calculate_outcome_interaction_private_professional,
            all_items,
            name="interaction_private_professional",
        ),
        Event(
            "A crew member addresses a teammate openly on the bridge.",
            None,
            0, None, None, locations["bridge"],
            calculate_outcome_interaction_public_professional,
            all_items,
            name="interaction_public_professional",
        ),
        Event(
            "Two crew members share a private personal exchange in their quarters.",
            None,
            0, None, None, locations["quarters"],
            calculate_outcome_interaction_private_personal,
            all_items,
            name="interaction_private_personal",
        ),
        Event(
            "Two crew members have a candid personal conversation in the mess hall.",
            None,
            0, None, None, locations["mess"],
            calculate_outcome_interaction_public_personal,
            all_items,
            name="interaction_public_personal",
        ),
        # Empty outcomes
        Event(
            "The team debates the wisdom of use of the drug midnight stare.",
            None,
            0, "intelligence", None, locations["crew quarters"],
            empty_outcome,
            all_items,
            name="midnight_stare_debate",
        ),
        Event(
            "The team languishes in their quarters, eager for the mission to begin.",
            None,
            0, "intelligence", None, locations["quarters"],
            empty_outcome,
            all_items,
            name="languish_quarters",
        ),
        # Crafting events
        Event(
            "A team member heads to the engineering bay to try upgrading a weapon.",
            "The work session ends.",
            0, None, "Weaponsmithing", locations["engineering"],
            calculate_outcome_weaponsmithing,
            all_items,
            name="weaponsmithing",
        ),
        Event(
            "A team member spends time in the workshop attempting to improve a piece of armor.",
            "The work session ends.",
            0, None, "Armorsmithing", locations["engineering"],
            calculate_outcome_armorsmithing,
            all_items,
            name="armorsmithing",
        ),
        Event(
            "A team member retreats to the tech lab to tinker with a piece of gear.",
            "The tinkering session wraps up.",
            0, None, "Tinkering", locations["tech lab"],
            calculate_outcome_tinkering,
            all_items,
            name="tinkering",
        ),
        # Found-items event
        Event(
            "The team discovers an unlocked supply room.",
            "The search is complete.",
            0, None, None, locations["supply room"],
            calculate_outcome_found_items,
            all_items,
            name="found_items",
        ),
    ]

    optional_singular_events = [
        # Skill check events
        # Compound Event
        Event(
            "A strange signal is detected on the sensors.",
            "The signal ends.",
            0, "intelligence", "Ships Systems", locations["bridge"],
            calculate_outcome_mysterious_sensor_signal,
            all_items,
        ),
        Event(
            "A rogue maintenance bot is damaging cables near the power node.",
            "The robot has been deactivated.",
            0, "intelligence", "Robot Repair", locations["engineering"],
            calculate_outcome_rogue_maintenance_bot,
            all_items,
        ),
        Event(
            "A fire breaks out in a cargo bay.",
            "The fire is extinguished.",
            0, None, "Ships Systems", locations["hangar"],
            calculate_outcome_ship_fire,
            all_items,
        ),
        Event(
            "An alien signal is intercepted.",
            "The signal has ended.",
            0, "intelligence", "Artifact Analysis", locations["communications"],
            calculate_outcome_alien_signal,
            all_items,
        ),
        Event(
            "An argument erupts in the corridor, threatening to come to physical blows.",
            "The argument subsides.",
            0, "leadership", "Social Engineering", locations["corridor"],
            calculate_outcome_ship_argument,
            all_items,
        ),
        Event(
            "An argument erupts in the crew quarters, threatening to come to physical blows.",
            "The argument subsides.",
            0, "leadership", "Social Engineering", locations["crew quarters"],
            calculate_outcome_ship_argument,
            all_items,
        ),
        Event(
            "An unexpected debris field blocks the Knacknarpia.",
            "The debris field is passed.",
            0, "coordination", "Piloting", locations["bridge"],
            calculate_outcome_avoid_debris,
            all_items,
        ),
        Event(
            "Alarms blare — a coolant breach has contaminated the fusion reactor.",
            "The reactor situation has been resolved.",
            0, "intelligence", "Physics", locations["engineering"],
            calculate_outcome_fusion_reactor,
            all_items,
        ),
        Event(
            "A plasma torpedo in the ship's magazine has become dangerously unstable.",
            "The torpedo threat has been dealt with.",
            0, "coordination", "Explosives", locations["hangar"],
            calculate_outcome_plasma_torpedo,
            all_items,
        ),
        # Empty outcomes — (moved to required_singular_events below)
    ]

    # required_singular_events: guaranteed to fire exactly once.
    # Scheduled at a random step in [2, max_events-1].
    required_singular_events = [
        Event(
            "Situation critical. We have run out of Oreos.",
            "There is no recourse.",
            0, None, "Supply Logistics", locations["mess"],
            calculate_outcome_out_of_oreos,
            all_items,
        ),
    ]

    rando_atmosphere_strings = [
        " the vastness of space overwhelms the crew, causing a combination of awe and anxiety.",
        " the tiny confines of the Knacknarpia press in on the crew, causing them to feel trapped.",
        " the meager selection of food begins to annoy the crew.",
        " the crew plays a virtual Starcraft tournament to pass the time.",
        " the team debates whether or not life is a simulation.",
        " despite the best life support, the air in the ship is stale.",
        " data drops from the frontier become fewer and far between.",
        " the crew hypothesizes about that intermittent creaking sound in the bulkhead.",
        f" {team[random.randint(0, len(team) - 1)].name} regales the crew with tales of past glory.",
        " the Knacknarpia has become home for the team until they reach the mission point.",
        " the team starts to doubt if their mission can be accomplished.",
        f" {team[random.randint(0, len(team) - 1)].name} has a dream they are convinced is an alien warning to turn back.",
    ]

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))
    stage = 4

    day = 1
    voyage_complete = False
    # Display the day
    await drawContext.display_message(f"DAY {day}", "default", (40, 10))
    await drawContext.display_message("The voyage of Knacknarpia to mission point", "default", (140, 10))

    intro_text = "The voyage to the mission point begins... click to proceed."
    await type_out_text(screen, intro_text, DEFAULT_FONT)

    events_completed = 0
    max_events_in_voyage = random.randint(25, 32)
    speech_done = False
    last_repeatable_event_name = None

    # Pre-schedule trigger points for required events (not at step 0 or the last step)
    _req_count   = len(required_singular_events)
    _available   = list(range(2, max_events_in_voyage))
    _req_triggers = set(
        random.sample(_available, min(_req_count, len(_available)))
    )

    screen.blit(EXIT_TEXT, EXIT_RECT)
    # Event Loop
    running = True
    waiting = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False
                else:
                    waiting = False
                    await update_screen(screen, background_image, day, DEFAULT_FONT)
                    screen.blit(EXIT_TEXT, EXIT_RECT)
                    if not voyage_complete:
                        rando_text = ""
                        if rando_atmosphere_strings and random.randint(0, 100) < 30:
                            rando_index = random.randint(0, len(rando_atmosphere_strings) - 1)
                            rando_text = rando_atmosphere_strings.pop(rando_index)
                        await type_out_text(screen, "The voyage continues..." + rando_text, DEFAULT_FONT)
                    else:
                        running = False
                        waiting = True

        # Move to next event
        if not waiting:
            location = locations[random.choice(list(locations.keys()))]
            if not speech_done:
                # Always-first event: inspirational speech
                speech_done = True
                draw_location(locations["mess"], screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                await calculate_outcome_inspirational_speech(team, None, None, screen, DEFAULT_FONT)
                await type_out_text(screen, "Click to proceed.", DEFAULT_FONT)
                events_completed += 1
                day += 1
            elif events_completed > max_events_in_voyage:
                # Force any remaining required events before declaring arrival
                if required_singular_events:
                    req_event = required_singular_events.pop(0)
                    location = req_event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    await req_event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                else:
                    await type_out_text(screen, "You have arrived at the destination!", DEFAULT_FONT)
                    voyage_complete = True
            else:
                # Fire a scheduled required event if this step is a trigger point
                if required_singular_events and events_completed in _req_triggers:
                    req_event = required_singular_events.pop(0)
                    location = req_event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    await req_event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                else:
                    selector = random.randint(0, 99)
                    if selector < 55:
                        event = build_procedural_training_event(team, locations, all_items, calculate_outcome_training)
                        if event.name == last_repeatable_event_name:
                            event = build_procedural_training_event(team, locations, all_items, calculate_outcome_training)
                        last_repeatable_event_name = event.name
                        location = event.context.location
                        draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                        await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                        events_completed += 1
                        day += 1
                    elif selector < 80:
                        # Don't repeat the same repeatable event back-to-back
                        available = repeatable_events if len(repeatable_events) == 1 else \
                            [e for e in repeatable_events if e.name != last_repeatable_event_name]
                        event = random.choice(available)
                        last_repeatable_event_name = event.name
                        location = event.context.location
                        draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                        await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                        events_completed += 1
                        day += 1
                    elif optional_singular_events:
                        event_index = random.randint(0, len(optional_singular_events) - 1)
                        event = optional_singular_events.pop(event_index)
                        location = event.context.location
                        draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                        await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                        if _fusion_reactor_failed:
                            max_events_in_voyage += 2
                            globals()['_fusion_reactor_failed'] = False
                        events_completed += 1
                        day += 1
                    else:
                        events_completed = max_events_in_voyage
                        day += 1
            waiting = True

        # Update the display
        pygame.display.flip()
        await asyncio.sleep(0)

    # Save characters upon exit
    if stage < 1000:
        team_data = save_team_named(team_name, loop, 4, team)

    pygame.quit()

    return stage + 1, team_data

async def main():
    print("Starting Stage: Voyage")
    team_data = voyage(None)

if __name__ == "__main__":
    main()

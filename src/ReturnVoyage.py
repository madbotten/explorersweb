import pygame
import os
import random
import pickle
import asyncio
import sys

from Character import Character
from Location import *
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

async def update_screen(surface, background, day, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"DAY {day}", True, CYAN)
    surface.blit(day_text, (40, TOP_BAR_Y))
    ship_text = font.render("The voyage of Knacknarpia to mission point", True, CYAN)
    surface.blit(ship_text, (140, TOP_BAR_Y))
    reset_text_offsets()

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

async def empty_outcome(team, stat_name, skill_name, screen, font):
    return

async def calculate_outcome_weaponsmithing(team, stat_name, skill_name, screen, font):
    """A skilled team member tries to upgrade the class of a weapon."""
    all_items = load_items()
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
    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    await type_out_text(screen, f"{member.name} sets to work in the engineering bay, attempting to upgrade {owner.name}'s {target_item.name}:", font)
    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)
    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(screen, f"Success! The weapon has been upgraded to {upgraded.name}. {member.name}'s Weaponsmithing skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(screen, f"{member.name} worked diligently, but the weapon is already at its peak quality.", font)
    else:
        await type_out_text(screen, f"{member.name} worked hard but couldn't achieve the desired improvement. The weapon is unchanged.", font, RED)

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
            await type_out_text(screen, f"Success! The armor has been upgraded to {upgraded.name}. {member.name}'s Armorsmithing skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(screen, f"{member.name} worked carefully, but the armor is already peak quality.", font)
    else:
        await type_out_text(screen, f"{member.name} gave it their best effort but couldn't achieve an improvement. The armor is unchanged.", font, RED)

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
            await type_out_text(screen, f"Success! The item has been upgraded to {upgraded.name}. {member.name}'s Tinkering skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(screen, f"{member.name} couldn't find a way to improve it further — the item is already at peak quality.", font)
    else:
        await type_out_text(screen, f"{member.name} tinkered away but couldn't figure out the right approach. The item is unchanged.", font, RED)

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

        # Find active commander (or exec / highest-leadership fallback) non-combatant to mediate.
        eligible = [
            m for m in team
            if m is not initiator and m is not target and not m.is_robot()
        ]
        mediator = get_active_commander(eligible)

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
    """Step 6: The highest-leadership non-robot addresses the crew before the return voyage.

    Success: every non-robot crew member gains 5-20 relationship points with
             every other crew member, and +5 morale.
    Failure: nothing happens.
    """
    non_robots = [m for m in team if not m.is_robot()]
    if not non_robots:
        await type_out_text(screen, "There is no one suitable to address the crew.", font)
        return

    leader = get_active_commander(non_robots)
    if leader is None:
        await type_out_text(screen, "There is no one suitable to address the crew.", font)
        return
    await type_out_text(screen, f"{leader.name} addresses the crew before the return voyage:", font)

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

async def calculate_outcome_psychotic_attack(team, stat_name, skill_name, screen, font):
    """Return voyage required event (conditional): a psychotic crew member snaps.

    Only runs if at least one team member has self.psychotic == True.
    Strongest psycho (highest offense) is chosen when multiple exist.

    Round structure:
      1. Perception check (best perceiver, difficulty -20).
         Pass → psycho spotted and thrown in the brig. Done.
      2. Fail → pick a random victim (non-robot, alive, not the psycho).
         Opposed surprise roll; victim loses → psycho gets +30 offense.
         Opposed offense roll (+ d30 each side).
         Psycho wins → victim takes damage; click to continue rampage.
         Victim wins → psycho subdued and thrown in the brig. Done.
      3. Repeat until brig, defeat, or all non-robots incapacitated.
    """
    psychotics = [m for m in team
                  if getattr(m, 'psychotic', False) and not m.is_robot()
                  and m.current_health > 0]
    if not psychotics:
        return  # no psychotic crew members — event is a no-op

    # Strongest psycho goes on the rampage
    psycho = max(psychotics, key=lambda m: m.stats.get("offense", 0))

    await type_out_text(
        screen,
        f"ALERT: {psycho.name} has snapped! A psychotic episode is unfolding!",
        font, RED,
    )

    def alive_crew():
        """Non-robot, non-psycho, still conscious crew members."""
        return [m for m in team
                if m is not psycho and not m.is_robot() and m.current_health > 0]

    # -----------------------------------------------------------------------
    # Rampage loop — each iteration is one round
    # -----------------------------------------------------------------------
    while True:
        # 1. Perception check — can anyone spot the threat?
        candidates = alive_crew()
        if not candidates:
            await type_out_text(
                screen,
                "All crew members are incapacitated. Mission is in grave danger!",
                font, RED,
            )
            await mission_failure(screen, font)
            return

        perceiver = max(candidates, key=lambda m: m.stats.get("perception", 0))
        roll = random.randint(1, 100)
        perceived = perceiver.stat_check(roll, "perception", -20)

        if perceived:
            await type_out_text(
                screen,
                f"{perceiver.name}'s keen awareness spots the danger in time. "
                f"{psycho.name} is restrained and thrown in the brig.",
                font, GREEN,
            )
            team.remove(psycho)
            return

        pacifier_holder = next((m for m in candidates if m.has_item("pacifier")), None)
        if pacifier_holder is not None:
            await type_out_text(
                screen,
                f"{pacifier_holder.name} reacts quickly with a pacifier, incapacitating {psycho.name} before anyone is harmed! "
                f"{psycho.name} is restrained and thrown in the brig.",
                font, GREEN,
            )
            team.remove(psycho)
            return

        await type_out_text(
            screen,
            f"{perceiver.name} fails to notice the warning signs. The attack continues!",
            font, RED,
        )

        # 2. Pick a victim
        victims = alive_crew()
        if not victims:
            await type_out_text(
                screen, "No one remains to stop the rampage. Mission failed!", font, RED)
            await mission_failure(screen, font)
            return

        victim = random.choice(victims)

        # 3. Surprise check (opposed roll + surprise stat)
        victim_surprise = random.randint(1, 100) + victim.stats.get("surprise", 0)
        psycho_surprise = random.randint(1, 100) + psycho.stats.get("surprise", 0)
        surprised = victim_surprise < psycho_surprise

        surprise_desc = (
            f"{victim.name} is caught completely off guard!"
            if surprised else
            f"{victim.name} senses something is wrong!"
        )
        await type_out_text(
            screen,
            f"{psycho.name} ambushes {victim.name}! {surprise_desc}",
            font, RED,
        )

        # 4. Offense check (d30 + stat; psycho gets +30 if victim surprised)
        psycho_offense = psycho.stats.get("offense", 50) + (30 if surprised else 0)
        psycho_roll    = random.randint(1, 30) + psycho_offense
        victim_roll    = random.randint(1, 30) + victim.stats.get("offense", 50)

        if psycho_roll > victim_roll:
            # Psycho wins — victim is killed instantly
            victim.current_health = 0
            await type_out_text(
                screen,
                f"{psycho.name} overwhelms {victim.name}! "
                f"{victim.name} is dead.",
                font, RED,
            )
            await type_out_text(screen, "Click to continue...", font)
            # Loop back — next round starts with a fresh perception check
        else:
            # Victim wins — psycho is subdued
            await type_out_text(
                screen,
                f"{victim.name} fights back and manages to subdue {psycho.name}! "
                f"{psycho.name} is restrained and thrown in the brig.",
                font, GREEN,
            )
            team.remove(psycho)
            return


async def calculate_outcome_traitor_sabotage(team, stat_name, skill_name, screen, font):
    """Return voyage required event (conditional): traitor(s) attempt sabotage.

    Only runs if at least one crew member has self.traitor == True.
    Multiple traitors work together, adding -10 difficulty per extra traitor.

    Step 1 — Commander perception check (difficulty -(traitors-1)*10):
      Pass  → plot foiled; traitors brigged; commander earns mission points;
               Interrogation roll for bonus points.

    Step 2 — Perception fails; traitors steal mission data.
              Commander surprise check (roll < surprise/2):
      Pass  → traitors caught fleeing; brigged; Interrogation roll for smaller bonus.

    Step 3 — Both checks fail:
              Traitors escape with stolen data; team loses 66% of mission points.
    """
    traitors = [m for m in team
                if getattr(m, 'traitor', False) and not m.is_robot()]
    if not traitors:
        return

    non_robots = [m for m in team if not m.is_robot() and m.current_health > 0]
    if not non_robots:
        return

    commander = get_active_commander(non_robots)
    if commander in traitors:
        commander = get_active_commander([m for m in non_robots if m is not commander])
    if commander is None:
        return
    traitor_names = " and ".join(t.name for t in traitors)
    plural = len(traitors) > 1

    await type_out_text(
        screen,
        f"INTELLIGENCE ALERT: A conspiracy has been uncovered aboard the Knacknarpia! "
        f"{traitor_names} {'have' if plural else 'has'} been plotting against the mission.",
        font, RED,
    )

    # -----------------------------------------------------------------
    # Helper: run interrogation roll and award bonus mission points
    # -----------------------------------------------------------------
    async def try_interrogation(bonus_per_traitor, context_msg):
        interrogator = determine_best_team_member(
            [m for m in team if m not in traitors and not m.is_robot()],
            None, "Interrogation",
        )
        if not interrogator:
            return
        await type_out_text(screen,
            f"{interrogator.name} begins interrogating the captured traitor(s)...", font)
        if await standard_skill_check(interrogator, screen, None, "Interrogation", font, 0):
            bonus = bonus_per_traitor * len(traitors)
            interrogator.mission_points += bonus
            await type_out_text(
                screen,
                f"{context_msg} +{bonus} mission points for {interrogator.name}.",
                font, GREEN,
            )

    # -----------------------------------------------------------------
    # Step 1: Commander perception check
    # -----------------------------------------------------------------
    difficulty_modifier = -(len(traitors) - 1) * 10   # harder with more traitors
    roll = random.randint(1, 100)
    if commander.stat_check(roll, "perception", difficulty_modifier):
        await type_out_text(
            screen,
            f"{commander.name}'s sharp instincts expose the plot before any damage is done! "
            f"{traitor_names} {'are' if plural else 'is'} thrown in the brig.",
            font, GREEN,
        )
        points = 10 * len(traitors)
        commander.mission_points += points
        await type_out_text(
            screen,
            f"{commander.name} earns {points} mission points for foiling the conspiracy.",
            font, GREEN,
        )
        await try_interrogation(15, "The interrogation yields critical intelligence!")
        for t in traitors:
            team.remove(t)
        return

    # -----------------------------------------------------------------
    # Step 2: Perception failed — traitors steal mission data
    # -----------------------------------------------------------------
    await type_out_text(
        screen,
        f"{commander.name} failed to anticipate the conspiracy in time. "
        f"{traitor_names} steal valuable mission data and materials!",
        font, RED,
    )

    loyal_crew = [m for m in non_robots if m not in traitors]
    pacifier_holder = next((m for m in loyal_crew if m.has_item("pacifier")), None)
    if pacifier_holder is not None:
        await type_out_text(
            screen,
            f"{pacifier_holder.name} deploys a pacifier to incapacitate the fleeing traitor(s)! "
            f"{traitor_names} {'are' if plural else 'is'} captured and thrown in the brig.",
            font, GREEN,
        )
        await try_interrogation(10, "Despite the stolen data, the interrogation recovers some intelligence.")
        for t in traitors:
            team.remove(t)
        return

    surprise_threshold = commander.stats.get("surprise", 0) / 2
    surprise_roll = random.randint(1, 100)
    if surprise_roll < surprise_threshold:
        await type_out_text(
            screen,
            f"{commander.name}'s quick reflexes catch the traitor(s) before they can escape! "
            f"{traitor_names} {'are' if plural else 'is'} captured and thrown in the brig.",
            font, GREEN,
        )
        await try_interrogation(10, "Despite the stolen data, the interrogation recovers some intelligence.")
        for t in traitors:
            team.remove(t)
        return

    # -----------------------------------------------------------------
    # Step 3: Both checks failed — traitors escape
    # -----------------------------------------------------------------
    await type_out_text(
        screen,
        f"{commander.name} was too slow to react. "
        f"{traitor_names} {'escape' if plural else 'escapes'} with the stolen mission data!",
        font, RED,
    )
    lost_total = 0
    for m in non_robots:
        lost = int(m.mission_points * 0.66)
        m.mission_points = max(0, m.mission_points - lost)
        lost_total += lost
    await type_out_text(
        screen,
        f"The team has lost 66% of their mission points due to the stolen data. "
        f"({lost_total} points lost)",
        font, RED,
    )


async def return_voyage(team_data, team_name="Debug Team", loop=1) :
    global max_height
    global locations

    reset_text_offsets()
    max_height = SCREEN_HEIGHT - CREDITS_BAR_HEIGHT

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Voyage")
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)
    LOCATION_FONT = pygame.font.Font(font_path, 18)
    SMALL_FONT = pygame.font.Font(font_path, 12)
    EXIT_RECT = pygame.Rect(1330, TOP_BAR_Y, 105, 25)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 6)
    team = [Character.from_dict(data) for data in team_data]
    for character in team:
        character.team = team

    # Resize portraits to fit into a small area for each character
    for character in team:
        if character.portrait:
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
            "The team recuperates in their quarters, pondering what comes next.",
            None,
            0, "intelligence", None, locations["quarters"],
            empty_outcome,
            all_items,
            name="recuperate_quarters",
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
    ]

    optional_singular_events = [
        # (no optional singular events yet for the return voyage)
    ]

    # required_singular_events: only scheduled when the condition is met.
    # Phase 3: psycho attack fires if any crew member is psychotic.
    # Phase 4: traitor sabotage fires if any crew member is a traitor.
    required_singular_events = []

    _psychotics = [m for m in team
                   if getattr(m, 'psychotic', False) and not m.is_robot()]
    if _psychotics:
        required_singular_events.append(Event(
            "A crew member has snapped!",
            "The incident is resolved.",
            0, None, None, locations["crew quarters"],
            calculate_outcome_psychotic_attack,
            all_items,
        ))

    _traitors = [m for m in team if getattr(m, 'traitor', False) and not m.is_robot()]
    if _traitors:
        required_singular_events.append(Event(
            "A conspiracy has been uncovered!",
            "The conspiracy situation is resolved.",
            0, None, None, locations["bridge"],
            calculate_outcome_traitor_sabotage,
            all_items,
        ))

    rando_atmosphere_strings = [
        " the vastness of space overwhelms the crew, causing a combination of awe and anxiety.",
        " the tiny confines of the Knacknarpia press in on the crew, causing them to feel trapped.",
        " the meager selection of food begins to annoy the crew.",
        " the crew plays a virtual Starcraft tournament to pass the time.",
        " the team debates whether or not life is a simulation.",
        " despite the best life support, the air in the ship is stale.",
        " data drops from the frontier become fewer and far between.",
        " the crew hypothesizes about the source of that intermittent creaking sound in the bulkhead.",
        f" {team[random.randint(0, len(team) - 1)].name} regales the crew with tales of past glory.",
        " the Knacknarpia has become home for the team until they reach the mission point.",
        " the team starts to doubt if their mission can be accomplished.",
        f" {team[random.randint(0, len(team) - 1)].name} has a dream they are convinced is an alien warning to turn back.",
    ]

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))
    stage = 7

    day = 1
    voyage_complete = False
    # Display the day
    day_text = DEFAULT_FONT.render(f"DAY {day}", True, CYAN)
    screen.blit(day_text, (40, TOP_BAR_Y))
    ship_text = DEFAULT_FONT.render("The voyage of Knacknarpia to home base", True, CYAN)
    screen.blit(ship_text, (140, TOP_BAR_Y))

    intro_text = "The return voyage to home base begins... click to proceed."
    await type_out_text(screen, intro_text, DEFAULT_FONT)

    events_completed = 0
    max_events_in_voyage = random.randint(10, 15)
    speech_done = False
    last_repeatable_event_name = None

    # Pre-schedule trigger points for required events (not at step 0 or the last step)
    _req_count = len(required_singular_events)
    _available = list(range(2, max_events_in_voyage))  # steps 2..max-1
    _req_triggers = set(
        random.sample(_available, min(_req_count, len(_available)))
    )

    # Event Loop
    running = True
    waiting = True
    while running:
        for event in pygame.event.get():
            if team_dead(team):
                await mission_failure(screen, DEFAULT_FONT)
                running = False
                stage = 999  # sentinel: return to load screen
                break

            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False
                else:
                    play_positive_click()
                    waiting = False
                    await update_screen(screen, background_image, day, DEFAULT_FONT)
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
                        events_completed += 1
                        day += 1
                    else:
                        events_completed = max_events_in_voyage
                        day += 1
            waiting = True

        # Update the display
        screen.blit(EXIT_TEXT, EXIT_RECT)
        pygame.display.flip()
        await asyncio.sleep(0)

    # Save characters upon exit (only on clean exit, not team death/quit)
    if stage not in (999, 1000):
        team_data = save_team_named(team_name, loop, 7, team)

    return stage + 1, team_data

async def main():
    print("Starting Stage: Return Voyage")
    team_data = return_voyage(None)

if __name__ == "__main__":
    main()

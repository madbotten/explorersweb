import pygame
import os
import random
import pickle
import time
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

def update_screen(surface, background, day, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"DAY {day}", True, CYAN)
    surface.blit(day_text, (40, 10))
    ship_text = font.render("The voyage of Knacknarpia to mission point", True, CYAN)
    surface.blit(ship_text, (140, 10))
    reset_text_offsets()

def calculate_outcome_mysterious_sensor_signal(team, stat_name, skill_name, screen, font):
    # Determine the best team member to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} responds by examining the sensor data:", font)
    else:
        type_out_text(screen, "No suitable team members found to address the event.", font)
        type_out_text(screen, "The Knacknarpia flies through a debris field due to a lack of warning.\nThe crew sustains minor injuries.", font)
        for member in team:
            if member:
                member.hurt(10, "impact")
        return

    # Run a skill check
    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} determines that a course correction is needed to avoid interstellar debris.\n "
        member.increase_skill(skill_name, 3)
        type_out_text(screen, result_text, font)
    else:
        result_text = f"{member.name} fails to understand the problem.\nKnacknarpia flies through a debris field. Team sustains minor injuries."
        type_out_text(screen, result_text, font)
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

def calculate_outcome_training(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} {random.choice(teacher_responds_statements)}", font)
    else:
        type_out_text(screen, random.choice(no_suitable_statements), font)
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
    type_out_text(screen, roll_string(roll, skill_name, stat_name, modifier), font, color)

    if skill_check:
        result_text = f"{member.name} {random.choice(teaches_statements)}\n(Mission points + 1)"
        member.mission_points += 1
        for member in team:
          member.increase_skill(skill_name, 2)
          member.encourage(1)
    else:
        result_text = f"{member.name} {random.choice(train_fail_statements)}\n "

    type_out_text(screen, result_text, font, WHITE)

def calculate_outcome_rogue_maintenance_bot(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} responds by remote shutdown of the bot:", font)
    else:
        type_out_text(screen, "No suitable team members found to shutdown rogue machine.", font)
        type_out_text(screen, "The Knacknarpia's power systems are damaged. The journey will take longer.", font)
        for member in team:
            if member:
                 member.demoralize(5)
        return

    # Simulate a skill check
    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, 0)

    if check_passed:
        result_text = f"{member.name} makes a rapid code correction. The crew is safe.\nTheir robotics skill increases."
        member.increase_skill(skill_name, 3)
    else:
        result_text = f"{member.name} could not stop the robot in time.\nThe ship sustains damage."
        for member in team:
            if member:
                 member.demoralize(5)

    type_out_text(screen, result_text, font, WHITE)

def calculate_outcome_avoid_debris(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} responds by rapid change of course:", font)
    else:
        type_out_text(screen, "No suitable team members found to implement emergency course change.", font)
        type_out_text(screen, "The Knacknarpia flies through a debris field due to a lack of warning. The crew sustains minor injuries.", font)
        for member in team:
            if member:
                 member.hurt(10, "impact")
        return

    # Simulate a skill check
    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} makes a rapid course correction. The crew is safe.\nTheir piloting skill increases."
        member.increase_skill(skill_name, 3)
        member.encourage(1)
    else:
        result_text = f"{member.name} changed course but threw the crew around.\nTeam sustains minor injuries."
        for member in team:
            if member:
                 member.hurt(5, "impact")

    type_out_text(screen, result_text, font, WHITE)

def calculate_outcome_alien_signal(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} analyzes the mysterious signal:", font)
    else:
        type_out_text(screen, "No suitable team members found to decode it.\nThe message will be turned in when the crew returns home.", font)
        return

    # Simulate a skill check
    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} decodes the message, learning the location of an alien colony. (+20 mission points)\nTheir skill increases."
        member.mission_points += 20
        member.increase_skill(skill_name, 5)
        member.encourage(5)
    else:
        result_text = f"{member.name} could not decipher the message.\nIt will be stored for analysis upon return home."
        member.demoralize(2)

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

def calculate_outcome_ship_argument(team, stat_name, skill_name, screen, font):
    modifier = 0
    for member in team:
        if member.is_combative_personality():
            modifier -= 10

    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} responds by intervening:", font)
    else:
        type_out_text(screen, "No suitable team members found to address the event.", font)
        result_text = "The crew begins to brawl. The crew sustains minor injuries before they lose interest."
        type_out_text(screen, result_text, font, WHITE)
        for member in team:
            if member:
                member.hurt(10, "impact")
                member.demoralize(5)
        return

    # Simulate a skill check
    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, modifier)

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

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

def calculate_outcome_ship_fire(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} responds by activating a fire suppression system that was somehow left off:", font)
    else:
        type_out_text(screen, random.choice(no_suitable_team_member_statements), font)
        result_text = "Some of the crew's items have been destroyed."
        if team_has_item(team, "techbot"):
            result_text = "Some of the crew's items were damaged. The techbot was able to repair them."
        else:
            for i in range(0,2):
                member = random.choice(team)
                if member and len(member.equipment) > 0:
                    member.equipment.remove(random.choice(member.equipment))
        type_out_text(screen, result_text, font, WHITE)
        return

    # Simulate a skill check
    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -20)

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

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

def empty_outcome(team, stat_name, skill_name, screen, font):
    return

# Crafting events — one per skill
def calculate_outcome_weaponsmithing(team, stat_name, skill_name, screen, font):
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
        type_out_text(screen, "The team has no weapons that can be improved further.", font)
        return

    member = determine_best_team_member(team, stat_name, skill_name)
    if not member:
        type_out_text(screen, "No one on the team has Weaponsmithing skill to attempt an upgrade.", font)
        return

    # Pick the highest-effect weapon on the team as the target
    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    type_out_text(screen, f"{member.name} sets to work in the engineering bay, attempting to upgrade {owner.name}'s {target_item.name}:", font)

    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            type_out_text(screen, f"Success! The weapon has been upgraded to {upgraded.name}. {member.name}'s Weaponsmithing skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            type_out_text(screen, f"{member.name} worked diligently, but the weapon is already at its peak quality.", font)
    else:
        type_out_text(screen, f"{member.name} worked hard but couldn't achieve the desired improvement. The weapon is unchanged.", font, RED)

def calculate_outcome_armorsmithing(team, stat_name, skill_name, screen, font):
    """A skilled team member tries to upgrade the class of an armor item."""
    all_items = load_items()
    candidates = [
        (member, item)
        for member in team if not member.is_robot()
        for item in member.equipment
        if item.type == "armor" and item_class(item.name) != "S"
    ]
    if not candidates:
        type_out_text(screen, "The team has no armor that can be improved further.", font)
        return

    member = determine_best_team_member(team, stat_name, skill_name)
    if not member:
        type_out_text(screen, "No one on the team has Armorsmithing skill to attempt an upgrade.", font)
        return

    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    type_out_text(screen, f"{member.name} carefully examines {owner.name}'s {target_item.name} and begins reworking it:", font)

    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            type_out_text(screen, f"Success! The armor has been upgraded to {upgraded.name}. {member.name}'s Armorsmithing skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            type_out_text(screen, f"{member.name} worked carefully, but the armor is already peak quality.", font)
    else:
        type_out_text(screen, f"{member.name} gave it their best effort but couldn't achieve an improvement. The armor is unchanged.", font, RED)

def calculate_outcome_tinkering(team, stat_name, skill_name, screen, font):
    """A skilled team member tries to upgrade the class of a misc item."""
    all_items = load_items()
    candidates = [
        (member, item)
        for member in team if not member.is_robot()
        for item in member.equipment
        if item.type == "misc" and item_class(item.name) != "S"
    ]
    if not candidates:
        type_out_text(screen, "The team has no misc items that can be tinkered with further.", font)
        return

    member = determine_best_team_member(team, stat_name, skill_name)
    if not member:
        type_out_text(screen, "No one on the team has Tinkering skill to attempt an upgrade.", font)
        return

    _, target_item = max(candidates, key=lambda x: x[1].effect)
    owner = next(m for m, i in candidates if i is target_item)
    type_out_text(screen, f"{member.name} pulls out tools and starts tinkering with {owner.name}'s {target_item.name}:", font)

    check_passed = standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            type_out_text(screen, f"Success! The item has been upgraded to {upgraded.name}. {member.name}'s Tinkering skill increases.", font, GREEN)
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            type_out_text(screen, f"{member.name} couldn't find a way to improve it further — the item is already at peak quality.", font)
    else:
        type_out_text(screen, f"{member.name} tinkered away but couldn't figure out the right approach. The item is unchanged.", font, RED)

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

def _run_interaction(team, screen, font, setting_type, privacy_level):
    """Core logic shared by all four interaction event outcomes."""
    non_robots = [m for m in team if not m.is_robot()]
    if len(non_robots) < 2:
        type_out_text(screen, "The crew keeps to themselves.", font)
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

    emit_character_image_at_text_offset(initiator, screen)
    type_out_text(screen, result.sentence, font, WHITE)

    liked_by_score = target.interaction_liked_by.get(result.interaction_type, 0)
    reaction = _interaction_reaction_string(result.success, liked_by_score, target.name)
    color = GREEN if result.success else RED
    type_out_text(screen, reaction, font, color)

    if observer_list:
        names = ", ".join(m.name for m in observer_list)
        type_out_text(screen, f"Witnessed by: {names}.", font, CYAN)

    # --- Fight escalation (Step 5) ---
    if result.fight_triggered:
        type_out_text(
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
            type_out_text(screen, f"{mediator.name} steps in to break it up:", font)
            check_passed = standard_skill_check(
                mediator, screen, "leadership", "Social Engineering", font, 0
            )
            if check_passed:
                type_out_text(
                    screen,
                    f"{mediator.name} manages to calm things down. Their leadership is strengthened.",
                    font, GREEN,
                )
                mediator.increase_stat("leadership", 3)
                mediator.increase_skill("Social Engineering", 3)
                mediator.encourage(5)
            else:
                type_out_text(
                    screen,
                    f"{mediator.name} cannot stop them. The fight breaks out! Both sides take minor injuries.",
                    font, RED,
                )
                initiator.hurt(8, "impact")
                target.hurt(8, "impact")
                for m in team:
                    m.demoralize(3)
        else:
            type_out_text(
                screen,
                "No one steps in. The brawl breaks out! Both sides take injuries.",
                font, RED,
            )
            initiator.hurt(12, "impact")
            target.hurt(12, "impact")
            for m in team:
                m.demoralize(5)

def calculate_outcome_interaction_private_professional(team, stat_name, skill_name, screen, font):
    """PRIVATE PROFESSIONAL: a quiet work talk in crew quarters."""
    _run_interaction(team, screen, font, PROFESSIONAL, PRIVATE)

def calculate_outcome_interaction_public_professional(team, stat_name, skill_name, screen, font):
    """PUBLIC PROFESSIONAL: an open exchange on the bridge."""
    _run_interaction(team, screen, font, PROFESSIONAL, PUBLIC)

def calculate_outcome_interaction_private_personal(team, stat_name, skill_name, screen, font):
    """PRIVATE PERSONAL: a personal conversation behind closed doors."""
    _run_interaction(team, screen, font, PERSONAL, PRIVATE)

def calculate_outcome_interaction_public_personal(team, stat_name, skill_name, screen, font):
    """PUBLIC PERSONAL: a candid exchange in the mess hall."""
    _run_interaction(team, screen, font, PERSONAL, PUBLIC)

def calculate_outcome_inspirational_speech(team, stat_name, skill_name, screen, font):
    """Step 6: The highest-leadership non-robot addresses the crew before departure.

    Success: every non-robot crew member gains 5-20 relationship points with
             every other crew member, and +5 morale.
    Failure: nothing happens.
    """
    non_robots = [m for m in team if not m.is_robot()]
    if not non_robots:
        type_out_text(screen, "There is no one suitable to address the crew.", font)
        return

    leader = max(non_robots, key=lambda m: m.stats.get("leadership", 0))
    type_out_text(screen, f"{leader.name} addresses the crew before departure:", font)

    check_passed = standard_skill_check(leader, screen, "leadership", "Instruction", font, 0)

    if check_passed:
        boost = random.randint(5, 20)
        type_out_text(
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
        type_out_text(
            screen,
            f"{leader.name}'s words fall flat. The crew remains unmoved.",
            font, RED,
        )

def voyage(team_data) :
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
    EXIT_RECT = pygame.Rect(1330, 8, 105, 25)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team("team_data_stage_3.pkl")
    team = [Character.from_dict(data) for data in team_data]
    for character in team:
        character.team = team

    # Resize portraits to fit into a small area for each character
    for character in team:
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
        ),
        Event(
            "A crew member addresses a teammate openly on the bridge.",
            None,
            0, None, None, locations["bridge"],
            calculate_outcome_interaction_public_professional,
            all_items,
        ),
        Event(
            "Two crew members share a private personal exchange in their quarters.",
            None,
            0, None, None, locations["quarters"],
            calculate_outcome_interaction_private_personal,
            all_items,
        ),
        Event(
            "Two crew members have a candid personal conversation in the mess hall.",
            None,
            0, None, None, locations["mess"],
            calculate_outcome_interaction_public_personal,
            all_items,
        ),
        # Empty outcomes
        Event(
            "The team debates the wisdom of use of the drug midnight stare.",
            None,
            0, "intelligence", None, locations["crew quarters"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team languishes in their quarters, eager for the mission to begin.",
            None,
            0, "intelligence", None, locations["quarters"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team decides they would like to practice hacking.",
            None,
            0, None, "Hacking", locations["bridge"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team conducts a virtual shooting practice session in the holo room.",
            None,
            0, None, "Projectile Weapons", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team tries to manipulate each other to get their favorite food bars.",
            "Eventually everyone accepts their ration.",
            0, None, "Social Engineering", locations["mess"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team is restless and decide to spar in the holo room.",
            "The sparring is over.",
            0, None, "Martial Arts", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team plays hide and seek to pass the time.",
            "The time for games is over.",
            0, None, "Stealth", locations["supply room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "While eating in the mess hall, the team discusses what aliens they might encounter on the mission.",
            "The meal ends.",
            0, None, "Xenobiology", locations["mess"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team plans out how to conduct themselves on the mission.",
            None,
            0, None, "Squad Tactics", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team debates what model of combat mech is the most effective.",
            "The debate subsides.",
            0, None, "Mech Combat", locations["robot bay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team simulates flying maneuvers in the holo room.",
            "The training session is over.",
            0, None, "Piloting", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team attempts to bypass a simulated security system.",
            None,
            0, None, "Hacking", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices negotiating resource agreements with an AI facilitator.",
            None,
            0, None, "Negotiation", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team participates in a sharpshooting competition using holographic targets.",
            None,
            0, None, "Sharpshooting", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices infiltrating a simulated enemy facility.",
            None,
            0, None, "Stealth", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team learns advanced first aid techniques.",
            None,
            0, None, "Medicine", locations["sickbay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices using sonic weapons.",
            None,
            0, None, "Sonic Weapons", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team analyzes historical military conflicts in the planning room.",
            None,
            0, None, "Military Science", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team safely defuses a mock explosive device.",
            None,
            0, None, "Explosives", locations["hangar"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team experiments with prosthetic enhancements in the tech lab.",
            None,
            0, None, "Cybernetics", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team studies alien biology specimens in hydroponics.",
            None,
            0, None, "Xenobiology", locations["hydroponics"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices building shelters in a survival simulation.",
            None,
            0, None, "Survival", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team simulates high-stakes diplomatic negotiations with an AI moderator.",
            None,
            0, None, "Diplomacy", locations["communications"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices star map navigation.",
            None,
            0, None, "Navigation", locations["bridge"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team interrogates a simulated suspect to uncover vital information.",
            None,
            0, None, "Interrogation", locations["brig"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team repairs malfunctioning droids in the robot bay.",
            None,
            0, None, "Robot Repair", locations["robot bay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team works on repairing the ship's life support systems.",
            None,
            0, None, "Ships Systems", locations["life support"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices gathering intelligence from a simulated enemy base.",
            None,
            0, None, "Espionage", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team fabricates essential mission tools using the onboard fabricator.",
            None,
            0, None, "Fabrication", locations["engineering"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices using high-energy weapons in a controlled environment.",
            None,
            0, None, "Energy Weapons", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team solves complex physics problems to optimize their equipment.",
            None,
            0, None, "Physics", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team analyzes mock artifacts for potential functionality.",
            None,
            0, None, "Artifact Analysis", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team tests exoskeleton systems for improved mobility and strength.",
            None,
            0, None, "Exoskeleton Systems", locations["engineering"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team conducts an advanced medical emergency response drill.",
            None,
            0, None, "Medicine", locations["sickbay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team learns efficient methods for extracting resources in simulated terrain.",
            None,
            0, None, "Resource Extraction", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices detecting anomalies in a simulated operational environment.",
            None,
            0, None, "Detection", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        # Crafting events
        Event(
            "A team member heads to the engineering bay to try upgrading a weapon.",
            "The work session ends.",
            0, None, "Weaponsmithing", locations["engineering"],
            calculate_outcome_weaponsmithing,
            all_items,
        ),
        Event(
            "A team member spends time in the workshop attempting to improve a piece of armor.",
            "The work session ends.",
            0, None, "Armorsmithing", locations["engineering"],
            calculate_outcome_armorsmithing,
            all_items,
        ),
        Event(
            "A team member retreats to the tech lab to tinker with a piece of gear.",
            "The tinkering session wraps up.",
            0, None, "Tinkering", locations["tech lab"],
            calculate_outcome_tinkering,
            all_items,
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
            0, "intelligence", "Analysis", locations["communications"],
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
        # Empty outcomes
        Event(
            "Situation critical. We have run out of Oreos.",
            "There is no recourse.",
            0, "intelligence", None, locations["mess"],
            empty_outcome,
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
    stage = 4

    day = 1
    voyage_complete = False
    # Display the day
    drawContext.display_message(f"DAY {day}", "default", (40, 10))
    drawContext.display_message("The voyage of Knacknarpia to mission point", "default", (140, 10))

    intro_text = "The voyage to the mission point begins... click to proceed."
    type_out_text(screen, intro_text, DEFAULT_FONT)

    events_completed = 0
    max_events_in_voyage = random.randint(25, 32)
    speech_done = False
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
                    update_screen(screen, background_image, day, DEFAULT_FONT)
                    screen.blit(EXIT_TEXT, EXIT_RECT)
                    if not voyage_complete:
                        rando_text = ""
                        if rando_atmosphere_strings and random.randint(0, 100) < 30:
                            rando_index = random.randint(0, len(rando_atmosphere_strings) - 1)
                            rando_text = rando_atmosphere_strings.pop(rando_index)
                        type_out_text(screen, "The voyage continues..." + rando_text, DEFAULT_FONT)
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
                calculate_outcome_inspirational_speech(team, None, None, screen, DEFAULT_FONT)
                events_completed += 1
                day += 1
            elif events_completed > max_events_in_voyage:
                type_out_text(screen, "You have arrived at the destination!", DEFAULT_FONT)
                voyage_complete = True
            else:
                selector = random.randint(0, 100)
                if selector < 75:
                    event_index = random.randint(0, len(repeatable_events) - 1)
                    event = repeatable_events[event_index]
                    location = event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                elif optional_singular_events:
                    event_index = random.randint(0, len(optional_singular_events) - 1)
                    event = optional_singular_events.pop(event_index)
                    location = event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                else:
                    events_completed = max_events_in_voyage
                    day += 1
            waiting = True

        # Update the display
        pygame.display.flip()

    # Save characters upon exit
    if stage < 1000:
        team_data = save_team("team_data_stage_4.pkl", team)

    pygame.quit()

    return stage + 1, team_data

def main():
    print("Starting Stage: Voyage")
    team_data = voyage(None)

if __name__ == "__main__":
    main()

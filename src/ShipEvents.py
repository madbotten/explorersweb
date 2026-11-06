import random

from Location import load_ship_locations
from Item import load_items, item_class, upgrade_item_class, replace_item_in_inventory
from Utils import *
from Event import Event, mission_failure, calculate_outcome_found_items
from TypeText import *
from Interaction import Interaction, PRIVATE, PUBLIC, PERSONAL, PROFESSIONAL

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
    "None of the members are equipped to share their expertise.",
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

_fusion_reactor_failed = False


def consume_fusion_reactor_failed() -> bool:
    """Return True and reset flag if the fusion reactor check failed on this step."""
    global _fusion_reactor_failed
    if _fusion_reactor_failed:
        _fusion_reactor_failed = False
        return True
    return False


def build_rando_atmosphere_strings(team):
    """Build the list of ship atmosphere flavor strings using non-robot crew names."""
    human_crew = [m for m in team if not m.is_robot()] or team
    return [
        " the vastness of space overwhelms the crew, causing a combination of awe and anxiety.",
        " the tiny confines of the Knacknarpia press in on the crew, causing them to feel trapped.",
        " the meager selection of food begins to annoy the crew.",
        " the crew plays a virtual Starcraft tournament to pass the time.",
        " the team debates whether or not life is a simulation.",
        " despite the best life support, the air in the ship is stale.",
        " data drops from the frontier become fewer and far between.",
        " the crew hypothesizes about that intermittent creaking sound in the bulkhead.",
        f" {random.choice(human_crew).name} regales the crew with tales of past glory.",
        " the Knacknarpia has become home for the team until they reach the mission point.",
        " the team starts to doubt if their mission can be accomplished.",
        f" {random.choice(human_crew).name} has a dream they are convinced is an alien warning to turn back.",
    ]


async def empty_outcome(team, stat_name, skill_name, screen, font):
    return


async def calculate_outcome_training(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} {random.choice(teacher_responds_statements)}", font)
    else:
        await type_out_text(screen, random.choice(no_suitable_statements), font)
        return

    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    modifier = round(member.get_effective_skill_level("Instruction") / 2)
    skill_check = member.skill_check(roll, skill_name, modifier)
    color = GREEN if skill_check else RED
    await type_out_text(screen, roll_string(roll, skill_name, stat_name, modifier), font, color)

    if skill_check:
        result_text = f"{member.name} {random.choice(teaches_statements)}\n(Mission points + 1)"
        member.mission_points += 1
        for m in team:
            m.increase_skill(skill_name, 2)
            m.encourage(1)
    else:
        result_text = f"{member.name} {random.choice(train_fail_statements)}\n "

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()


async def calculate_outcome_mysterious_sensor_signal(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by examining the sensor data:", font)
    else:
        await type_out_text(screen, "No suitable team members found to address the event.", font)
        await type_out_text(
            screen,
            "The Knacknarpia flies through a debris field due to a lack of warning.\nThe crew sustains minor injuries.",
            font,
        )
        for m in team:
            if m:
                m.hurt(10, "impact")
        return

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} determines that a course correction is needed to avoid interstellar debris.\n "
        member.increase_skill(skill_name, 3)
        await type_out_text(screen, result_text, font)
    else:
        result_text = (
            f"{member.name} fails to understand the problem.\n"
            f"Knacknarpia flies through a debris field. Team sustains minor injuries."
        )
        await type_out_text(screen, result_text, font)
        for m in team:
            if m:
                m.hurt(5, "impact")
        reset_x_offset()
        return

    reset_x_offset()
    ship_locations = load_ship_locations()
    return Event(
        "An unexpected debris field blocks the Knacknarpia.",
        "The debris field is passed.",
        0,
        "coordination",
        "Piloting",
        ship_locations["bridge"],
        calculate_outcome_avoid_debris,
        None,
    )


async def calculate_outcome_rogue_maintenance_bot(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by remote shutdown of the bot:", font)
    else:
        await type_out_text(screen, "No suitable team members found to shutdown rogue machine.", font)
        await type_out_text(screen, "The Knacknarpia's power systems are damaged. The journey will take longer.", font)
        for m in team:
            if m:
                m.demoralize(5)
        return

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, 0)

    if check_passed:
        result_text = f"{member.name} makes a rapid code correction. The crew is safe.\nTheir robotics skill increases."
        member.increase_skill(skill_name, 3)
    else:
        result_text = f"{member.name} could not stop the robot in time.\nThe ship sustains damage."
        for m in team:
            if m:
                m.demoralize(5)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()


async def calculate_outcome_avoid_debris(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by rapid change of course:", font)
    else:
        await type_out_text(screen, "No suitable team members found to implement emergency course change.", font)
        await type_out_text(
            screen,
            "The Knacknarpia flies through a debris field due to a lack of warning. The crew sustains minor injuries.",
            font,
        )
        for m in team:
            if m:
                m.hurt(10, "impact")
        return

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} makes a rapid course correction. The crew is safe.\nTheir piloting skill increases."
        member.increase_skill(skill_name, 3)
        member.encourage(1)
    else:
        result_text = f"{member.name} changed course but threw the crew around.\nTeam sustains minor injuries."
        for m in team:
            if m:
                m.hurt(5, "impact")

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()


async def calculate_outcome_alien_signal(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} analyzes the mysterious signal:", font)
    else:
        await type_out_text(
            screen,
            "No suitable team members found to decode it.\nThe message will be turned in when the crew returns home.",
            font,
        )
        return

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = (
            f"{member.name} decodes the message, learning the location of an alien colony. (+20 mission points)\n"
            f"Their skill increases."
        )
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
    for m in team:
        if m.is_combative_personality():
            modifier -= 10

    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(screen, f"{member.name} responds by intervening:", font)
    else:
        await type_out_text(screen, "No suitable team members found to address the event.", font)
        result_text = "The crew begins to brawl. The crew sustains minor injuries before they lose interest."
        await type_out_text(screen, result_text, font, WHITE)
        for m in team:
            if m:
                m.hurt(10, "impact")
                m.demoralize(5)
        return

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, modifier)

    if check_passed:
        result_text = (
            f"{member.name} talks the fight down, mending the disagreement while preserving egos.\n"
            f"Their leadership has been strengthened."
        )
        member.increase_stat(stat_name, 3)
        member.increase_skill(skill_name, 3)
        member.encourage(5)
    else:
        result_text = (
            f"{member.name} could not stop them in time. Team sustains very minor injuries after a brawl.\n"
            f"The team loses respect for their leader."
        )
        for m in team:
            if m:
                m.hurt(10, "impact")
                m.demoralize(3)
        member.decrease_skill(skill_name, 3)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()


async def calculate_outcome_ship_fire(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        await type_out_text(
            screen,
            f"{member.name} responds by activating a fire suppression system that was somehow left off:",
            font,
        )
    else:
        await type_out_text(screen, random.choice(no_suitable_team_member_statements), font)
        result_text = "Some of the crew's items have been destroyed."
        if team_has_item(team, "techbot"):
            result_text = "Some of the crew's items were damaged. The techbot was able to repair them."
        else:
            for _ in range(2):
                m = random.choice(team)
                if m and len(m.equipment) > 0:
                    m.equipment.remove(random.choice(m.equipment))
        await type_out_text(screen, result_text, font, WHITE)
        return

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -20)

    if check_passed:
        result_text = f"{member.name} stops the fire quickly.\nTheir skill has been strengthened."
        member.increase_skill(skill_name, 5)
        member.encourage(1)
    else:
        result_text = f"{member.name} could not stop the fire in time.\nOne of the crew's items have been destroyed."
        if team_has_item(team, "techbot"):
            result_text = (
                f"{member.name} could not stop the fire in time.\n"
                f"One of the crew's items were damaged, but the techbot was able to repair them."
            )
        else:
            m = random.choice(team)
            if m and len(m.equipment) > 0:
                m.equipment.remove(random.choice(m.equipment))
                m.demoralize(3)

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()


async def calculate_outcome_fusion_reactor(team, stat_name, skill_name, screen, font):
    """A contaminated fusion reactor requires a physicist to stabilise it."""
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
        global _fusion_reactor_failed
        _fusion_reactor_failed = True

    await type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()


async def calculate_outcome_plasma_torpedo(team, stat_name, skill_name, screen, font):
    """A plasma torpedo in the magazine has become unstable and needs disarming."""
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
    await type_out_text(
        screen,
        f"{member.name} sets to work in the engineering bay, attempting to upgrade {owner.name}'s {target_item.name}:",
        font,
    )

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(
                screen,
                f"Success! The weapon has been upgraded to {upgraded.name}.\n{member.name}'s Weaponsmithing skill increases.",
                font,
                GREEN,
            )
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(
                screen,
                f"{member.name} worked diligently, but the weapon is already at its peak quality.\nThe weapon is unchanged.",
                font,
            )
    else:
        await type_out_text(
            screen,
            f"{member.name} worked hard but couldn't achieve the desired improvement.\nThe weapon is unchanged.",
            font,
            RED,
        )
    reset_x_offset()


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
    await type_out_text(
        screen,
        f"{member.name} carefully examines {owner.name}'s {target_item.name} and begins reworking it:",
        font,
    )

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(
                screen,
                f"Success! The armor has been upgraded to {upgraded.name}.\n{member.name}'s Armorsmithing skill increases.",
                font,
                GREEN,
            )
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(
                screen,
                f"{member.name} worked carefully, but the armor is already peak quality.\nThe armor is unchanged.",
                font,
            )
    else:
        await type_out_text(
            screen,
            f"{member.name} gave it their best effort but couldn't achieve an improvement.\nThe armor is unchanged.",
            font,
            RED,
        )
    reset_x_offset()


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
    await type_out_text(
        screen,
        f"{member.name} pulls out tools and starts tinkering with {owner.name}'s {target_item.name}:",
        font,
    )

    check_passed = await standard_skill_check(member, screen, stat_name, skill_name, font, -10)

    if check_passed:
        upgraded = upgrade_item_class(target_item, all_items)
        if upgraded and replace_item_in_inventory(owner, target_item, upgraded):
            await type_out_text(
                screen,
                f"Success! The item has been upgraded to {upgraded.name}.\n{member.name}'s Tinkering skill increases.",
                font,
                GREEN,
            )
            member.increase_skill(skill_name, 5)
            member.encourage(3)
        else:
            await type_out_text(
                screen,
                f"{member.name} couldn't find a way to improve it further — the item is already at peak quality.\nThe item is unchanged.",
                font,
            )
    else:
        await type_out_text(
            screen,
            f"{member.name} tinkered away but couldn't figure out the right approach.\nThe item is unchanged.",
            font,
            RED,
        )
    reset_x_offset()


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
    candidates = [m for m in non_robots if m is not initiator]
    if not candidates:
        return
    target = random.choice(candidates)

    if privacy_level == PUBLIC:
        bystanders = [m for m in non_robots if m is not initiator and m is not target]
        num_observers = random.randint(0, min(2, len(bystanders)))
        observer_list = random.sample(bystanders, num_observers)
    else:
        observer_list = []

    result = Interaction.resolve(
        initiator,
        target,
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
    reset_x_offset()

    if result.fight_triggered:
        await type_out_text(
            screen,
            f"{target.name} is furious and starts a fight with {initiator.name}!",
            font,
            RED,
        )

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
                    f"{mediator.name} manages to calm things down.\nTheir leadership is strengthened.",
                    font,
                    GREEN,
                )
                mediator.increase_stat("leadership", 3)
                mediator.increase_skill("Social Engineering", 3)
                mediator.encourage(5)
            else:
                await type_out_text(
                    screen,
                    f"{mediator.name} cannot stop them. The fight breaks out!\nBoth sides take minor injuries.",
                    font,
                    RED,
                )
                initiator.hurt(8, "impact")
                target.hurt(8, "impact")
                for m in team:
                    m.demoralize(3)
            reset_x_offset()
        else:
            await type_out_text(
                screen,
                "No one steps in. The brawl breaks out! Both sides take injuries.",
                font,
                RED,
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


async def calculate_outcome_inspirational_speech(
    team, stat_name, skill_name, screen, font, context_phrase="before departure"
):
    """The highest-leadership non-robot addresses the crew."""
    non_robots = [m for m in team if not m.is_robot()]
    if not non_robots:
        await type_out_text(screen, "There is no one suitable to address the crew.", font)
        return

    leader = get_active_commander(non_robots)
    if leader is None:
        await type_out_text(screen, "There is no one suitable to address the crew.", font)
        return
    await type_out_text(screen, f"{leader.name} addresses the crew {context_phrase}:", font)

    check_passed = await standard_skill_check(leader, screen, "leadership", "Instruction", font, 0)

    if check_passed:
        boost = random.randint(5, 20)
        await type_out_text(
            screen,
            f"{leader.name}'s words resonate with the crew.\n"
            f"The team feels inspired to work together toward a common goal.\n"
            f"(Relationships +{boost}, Morale +5)",
            font,
            GREEN,
        )
        for member in non_robots:
            member.encourage(5)
            for other in non_robots:
                if other is not member:
                    member.adjust_relationship(other.name, boost)
    else:
        await type_out_text(
            screen,
            f"{leader.name}'s words fall flat.\nThe crew remains unmoved.",
            font,
            RED,
        )
    reset_x_offset()


async def calculate_outcome_out_of_oreos(team, stat_name, skill_name, screen, font):
    """Required outbound event: Supply Logistics check to avert an Oreo shortage."""
    member = determine_best_team_member(team, None, "Supply Logistics")
    if member:
        await type_out_text(screen, f"{member.name} checks the supply manifest...", font)
        check_passed = await standard_skill_check(member, screen, None, "Supply Logistics", font, 0)
        if check_passed:
            await type_out_text(
                screen,
                f"Thanks to {member.name}'s careful rationing, Oreo supplies hold.\nCrisis averted.",
                font,
                GREEN,
            )
        else:
            await type_out_text(
                screen,
                "The Oreo supply has been exhausted.\nMorale suffers.",
                font,
                RED,
            )
            for m in team:
                if not m.is_robot():
                    m.demoralize(5)
        await type_out_text(screen, " ", font)
        reset_x_offset()
    else:
        await type_out_text(
            screen,
            "With no one skilled in Supply Logistics, the Oreo shortage hits the crew hard.",
            font,
            RED,
        )
        for m in team:
            if not m.is_robot():
                m.demoralize(5)


async def calculate_outcome_psychotic_attack(team, stat_name, skill_name, screen, font):
    """Return voyage required event (conditional): a psychotic crew member snaps."""
    psychotics = [
        m for m in team
        if getattr(m, "psychotic", False) and not m.is_robot() and m.current_health > 0
    ]
    if not psychotics:
        return

    psycho = max(psychotics, key=lambda m: m.stats.get("offense", 0))

    await type_out_text(
        screen,
        f"ALERT: {psycho.name} has snapped! A psychotic episode is unfolding!",
        font,
        RED,
    )

    def alive_crew():
        return [
            m for m in team
            if m is not psycho and not m.is_robot() and m.current_health > 0
        ]

    while True:
        candidates = alive_crew()
        if not candidates:
            await type_out_text(
                screen,
                "All crew members are incapacitated. Mission is in grave danger!",
                font,
                RED,
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
                font,
                GREEN,
            )
            team.remove(psycho)
            return

        pacifier_holder = next((m for m in candidates if m.has_item("pacifier")), None)
        if pacifier_holder is not None:
            await type_out_text(
                screen,
                f"{pacifier_holder.name} reacts quickly with a pacifier, incapacitating {psycho.name} before anyone is harmed! "
                f"{psycho.name} is restrained and thrown in the brig.",
                font,
                GREEN,
            )
            team.remove(psycho)
            return

        await type_out_text(
            screen,
            f"{perceiver.name} fails to notice the warning signs. The attack continues!",
            font,
            RED,
        )

        victims = alive_crew()
        if not victims:
            await type_out_text(
                screen, "No one remains to stop the rampage. Mission failed!", font, RED
            )
            await mission_failure(screen, font)
            return

        victim = random.choice(victims)

        victim_surprise = random.randint(1, 100) + victim.stats.get("surprise", 0)
        psycho_surprise = random.randint(1, 100) + psycho.stats.get("surprise", 0)
        surprised = victim_surprise < psycho_surprise

        surprise_desc = (
            f"{victim.name} is caught completely off guard!"
            if surprised
            else f"{victim.name} senses something is wrong!"
        )
        await type_out_text(
            screen,
            f"{psycho.name} ambushes {victim.name}! {surprise_desc}",
            font,
            RED,
        )

        psycho_offense = psycho.stats.get("offense", 50) + (30 if surprised else 0)
        psycho_roll = random.randint(1, 30) + psycho_offense
        victim_roll = random.randint(1, 30) + victim.stats.get("offense", 50)

        if psycho_roll > victim_roll:
            victim.current_health = 0
            await type_out_text(
                screen,
                f"{psycho.name} overwhelms {victim.name}! "
                f"{victim.name} is dead.",
                font,
                RED,
            )
            await type_out_text(screen, "Click to continue...", font)
        else:
            await type_out_text(
                screen,
                f"{victim.name} fights back and manages to subdue {psycho.name}! "
                f"{psycho.name} is restrained and thrown in the brig.",
                font,
                GREEN,
            )
            team.remove(psycho)
            return


async def calculate_outcome_traitor_sabotage(team, stat_name, skill_name, screen, font):
    """Return voyage required event (conditional): traitor(s) attempt sabotage."""
    traitors = [
        m for m in team if getattr(m, "traitor", False) and not m.is_robot()
    ]
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
        font,
        RED,
    )

    async def try_interrogation(bonus_per_traitor, context_msg):
        interrogator = determine_best_team_member(
            [m for m in team if m not in traitors and not m.is_robot()],
            None,
            "Interrogation",
        )
        if not interrogator:
            return
        await type_out_text(
            screen,
            f"{interrogator.name} begins interrogating the captured traitor(s)...",
            font,
        )
        if await standard_skill_check(interrogator, screen, None, "Interrogation", font, 0):
            bonus = bonus_per_traitor * len(traitors)
            interrogator.mission_points += bonus
            await type_out_text(
                screen,
                f"{context_msg}\n+{bonus} mission points for {interrogator.name}.",
                font,
                GREEN,
            )
        else:
            await type_out_text(
                screen,
                "The captured traitor(s) refuse to cooperate.\nNo additional intelligence is recovered.",
                font,
                RED,
            )
        reset_x_offset()

    difficulty_modifier = -(len(traitors) - 1) * 10
    roll = random.randint(1, 100)
    if commander.stat_check(roll, "perception", difficulty_modifier):
        await type_out_text(
            screen,
            f"{commander.name}'s sharp instincts expose the plot before any damage is done! "
            f"{traitor_names} {'are' if plural else 'is'} thrown in the brig.",
            font,
            GREEN,
        )
        points = 10 * len(traitors)
        commander.mission_points += points
        await type_out_text(
            screen,
            f"{commander.name} earns {points} mission points for foiling the conspiracy.",
            font,
            GREEN,
        )
        await try_interrogation(15, "The interrogation yields critical intelligence!")
        for t in traitors:
            team.remove(t)
        return

    await type_out_text(
        screen,
        f"{commander.name} failed to anticipate the conspiracy in time. "
        f"{traitor_names} steal valuable mission data and materials!",
        font,
        RED,
    )

    loyal_crew = [m for m in non_robots if m not in traitors]
    pacifier_holder = next((m for m in loyal_crew if m.has_item("pacifier")), None)
    if pacifier_holder is not None:
        await type_out_text(
            screen,
            f"{pacifier_holder.name} deploys a pacifier to incapacitate the fleeing traitor(s)! "
            f"{traitor_names} {'are' if plural else 'is'} captured and thrown in the brig.",
            font,
            GREEN,
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
            font,
            GREEN,
        )
        await try_interrogation(10, "Despite the stolen data, the interrogation recovers some intelligence.")
        for t in traitors:
            team.remove(t)
        return

    await type_out_text(
        screen,
        f"{commander.name} was too slow to react. "
        f"{traitor_names} {'escape' if plural else 'escapes'} with the stolen mission data!",
        font,
        RED,
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
        font,
        RED,
    )


def build_ship_event_catalog(locations, all_items) -> dict[str, Event]:
    """Single source of truth for all ship Events used across Voyage and ReturnVoyage."""
    return {
        # Shared interaction events
        "interaction_private_professional": Event(
            "A crew member pulls a teammate aside for a private work discussion.",
            None,
            0, None, None, locations["crew quarters"],
            calculate_outcome_interaction_private_professional,
            all_items,
            name="interaction_private_professional",
        ),
        "interaction_public_professional": Event(
            "A crew member addresses a teammate openly on the bridge.",
            None,
            0, None, None, locations["bridge"],
            calculate_outcome_interaction_public_professional,
            all_items,
            name="interaction_public_professional",
        ),
        "interaction_private_personal": Event(
            "Two crew members share a private personal exchange in their quarters.",
            None,
            0, None, None, locations["quarters"],
            calculate_outcome_interaction_private_personal,
            all_items,
            name="interaction_private_personal",
        ),
        "interaction_public_personal": Event(
            "Two crew members have a candid personal conversation in the mess hall.",
            None,
            0, None, None, locations["mess"],
            calculate_outcome_interaction_public_personal,
            all_items,
            name="interaction_public_personal",
        ),
        # Empty-outcome flavor events
        "midnight_stare_debate": Event(
            "The team debates the wisdom of use of the drug midnight stare.",
            None,
            0, "intelligence", None, locations["crew quarters"],
            empty_outcome,
            all_items,
            name="midnight_stare_debate",
        ),
        "languish_quarters": Event(
            "The team languishes in their quarters, eager for the mission to begin.",
            None,
            0, "intelligence", None, locations["quarters"],
            empty_outcome,
            all_items,
            name="languish_quarters",
        ),
        "recuperate_quarters": Event(
            "The team recuperates in their quarters, pondering what comes next.",
            None,
            0, "intelligence", None, locations["quarters"],
            empty_outcome,
            all_items,
            name="recuperate_quarters",
        ),
        # Shared crafting events
        "weaponsmithing": Event(
            "A team member heads to the engineering bay to try upgrading a weapon.",
            "The work session ends.",
            0, None, "Weaponsmithing", locations["engineering"],
            calculate_outcome_weaponsmithing,
            all_items,
            name="weaponsmithing",
        ),
        "armorsmithing": Event(
            "A team member spends time in the workshop attempting to improve a piece of armor.",
            "The work session ends.",
            0, None, "Armorsmithing", locations["engineering"],
            calculate_outcome_armorsmithing,
            all_items,
            name="armorsmithing",
        ),
        "tinkering": Event(
            "A team member retreats to the tech lab to tinker with a piece of gear.",
            "The tinkering session wraps up.",
            0, None, "Tinkering", locations["tech lab"],
            calculate_outcome_tinkering,
            all_items,
            name="tinkering",
        ),
        # Found-items event
        "found_items": Event(
            "The team discovers an unlocked supply room.",
            "The search is complete.",
            0, None, None, locations["supply room"],
            calculate_outcome_found_items,
            all_items,
            name="found_items",
        ),
        # Outbound singular skill-check events
        "mysterious_sensor_signal": Event(
            "A strange signal is detected on the sensors.",
            "The signal ends.",
            0, "intelligence", "Ships Systems", locations["bridge"],
            calculate_outcome_mysterious_sensor_signal,
            all_items,
            name="mysterious_sensor_signal",
        ),
        "rogue_maintenance_bot": Event(
            "A rogue maintenance bot is damaging cables near the power node.",
            "The robot has been deactivated.",
            0, "intelligence", "Robot Repair", locations["engineering"],
            calculate_outcome_rogue_maintenance_bot,
            all_items,
            name="rogue_maintenance_bot",
        ),
        "ship_fire": Event(
            "A fire breaks out in a cargo bay.",
            "The fire is extinguished.",
            0, None, "Ships Systems", locations["hangar"],
            calculate_outcome_ship_fire,
            all_items,
            name="ship_fire",
        ),
        "alien_signal": Event(
            "An alien signal is intercepted.",
            "The signal has ended.",
            0, "intelligence", "Artifact Analysis", locations["communications"],
            calculate_outcome_alien_signal,
            all_items,
            name="alien_signal",
        ),
        "ship_argument_corridor": Event(
            "An argument erupts in the corridor, threatening to come to physical blows.",
            "The argument subsides.",
            0, "leadership", "Social Engineering", locations["corridor"],
            calculate_outcome_ship_argument,
            all_items,
            name="ship_argument_corridor",
        ),
        "ship_argument_quarters": Event(
            "An argument erupts in the crew quarters, threatening to come to physical blows.",
            "The argument subsides.",
            0, "leadership", "Social Engineering", locations["crew quarters"],
            calculate_outcome_ship_argument,
            all_items,
            name="ship_argument_quarters",
        ),
        "avoid_debris": Event(
            "An unexpected debris field blocks the Knacknarpia.",
            "The debris field is passed.",
            0, "coordination", "Piloting", locations["bridge"],
            calculate_outcome_avoid_debris,
            all_items,
            name="avoid_debris",
        ),
        "fusion_reactor": Event(
            "Alarms blare — a coolant breach has contaminated the fusion reactor.",
            "The reactor situation has been resolved.",
            0, "intelligence", "Physics", locations["engineering"],
            calculate_outcome_fusion_reactor,
            all_items,
            name="fusion_reactor",
        ),
        "plasma_torpedo": Event(
            "A plasma torpedo in the ship's magazine has become dangerously unstable.",
            "The torpedo threat has been dealt with.",
            0, "coordination", "Explosives", locations["hangar"],
            calculate_outcome_plasma_torpedo,
            all_items,
            name="plasma_torpedo",
        ),
        # Required singular events
        "out_of_oreos": Event(
            "Situation critical. We have run out of Oreos.",
            "There is no recourse.",
            0, None, "Supply Logistics", locations["mess"],
            calculate_outcome_out_of_oreos,
            all_items,
            name="out_of_oreos",
        ),
        "psychotic_attack": Event(
            "A crew member has snapped!",
            "The incident is resolved.",
            0, None, None, locations["crew quarters"],
            calculate_outcome_psychotic_attack,
            all_items,
            name="psychotic_attack",
        ),
        "traitor_sabotage": Event(
            "A conspiracy has been uncovered!",
            "The conspiracy situation is resolved.",
            0, None, None, locations["bridge"],
            calculate_outcome_traitor_sabotage,
            all_items,
            name="traitor_sabotage",
        ),
    }


def build_voyage_event_sets(locations, all_items):
    """Return (repeatable_events, optional_singular_events, required_singular_events) for outbound Voyage."""
    catalog = build_ship_event_catalog(locations, all_items)
    repeatable_keys = (
        "interaction_private_professional",
        "interaction_public_professional",
        "interaction_private_personal",
        "interaction_public_personal",
        "midnight_stare_debate",
        "languish_quarters",
        "weaponsmithing",
        "armorsmithing",
        "tinkering",
        "found_items",
    )
    optional_singular_keys = (
        "mysterious_sensor_signal",
        "rogue_maintenance_bot",
        "ship_fire",
        "alien_signal",
        "ship_argument_corridor",
        "ship_argument_quarters",
        "avoid_debris",
        "fusion_reactor",
        "plasma_torpedo",
    )
    required_singular_keys = ("out_of_oreos",)
    return (
        [catalog[k] for k in repeatable_keys],
        [catalog[k] for k in optional_singular_keys],
        [catalog[k] for k in required_singular_keys],
    )


def build_return_voyage_event_sets(locations, all_items, team):
    """Return (repeatable_events, optional_singular_events, required_singular_events) for ReturnVoyage."""
    catalog = build_ship_event_catalog(locations, all_items)
    repeatable_keys = (
        "interaction_private_professional",
        "interaction_public_professional",
        "interaction_private_personal",
        "interaction_public_personal",
        "recuperate_quarters",
        "weaponsmithing",
        "armorsmithing",
        "tinkering",
    )
    optional_singular_events = []
    required_singular_events = []
    if any(getattr(m, "psychotic", False) and not m.is_robot() for m in team):
        required_singular_events.append(catalog["psychotic_attack"])
    if any(getattr(m, "traitor", False) and not m.is_robot() for m in team):
        required_singular_events.append(catalog["traitor_sabotage"])
    return (
        [catalog[k] for k in repeatable_keys],
        optional_singular_events,
        required_singular_events,
    )

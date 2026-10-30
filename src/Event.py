import pygame
import random
import asyncio

from Battle import *
from TypeText import *
from Character import *
from Utils import *
from constants import DEBUG

enemies_present_statements = [
    "Enemies are present! A battle breaks out.",
    "Enemies are present, weapons drawn!",
    "An alarm blares, and enemy forces rush into the room from a far door!",
    "The team encounters hostiles!",
    "Enemies block the team's path!",
    "Combat commences!"
    "A fight erupts!",
    "The team finds themselves face-to-face with a group of hostiles!"
]

def team_evades_notice(team):
    """Rolls to see if the team avoids being detected before combat.
    Returns True if the team slips by unnoticed."""
    if not team:
        return False
    total_evasion = 0
    total_weight = 0
    scanner_bonus = 0
    for m in team:
        ev = m.get_effective_combat_evasion()
        if m.is_alive() and getattr(m, "position", None) == "point_man":
            total_evasion += ev * 2
            total_weight += 2
            if getattr(m, "occupation", None) == "scoutbot":
                scanner_bonus += 10
        else:
            total_evasion += ev
            total_weight += 1
    avg_evasion = (total_evasion / total_weight) + scanner_bonus
    roll = random.randint(1, 100)
    evaded = roll < avg_evasion
    if DEBUG:
        print(f"Stealth check: roll={roll}, avg_evasion={avg_evasion:.1f}, evaded={evaded}")
    return evaded

async def mission_failure(screen, font):
    global mission_failed
    mission_failed = True
    play_defeat_sound()
    # Draw a full-screen MISSION FAILED banner
    screen.fill((0, 0, 0))
    big_font = pygame.font.Font(resource_path("fonts/Orbitron-Bold.ttf"), 48)
    sub_font  = pygame.font.Font(resource_path("fonts/Orbitron-Bold.ttf"), 20)
    banner = big_font.render("MISSION FAILED", True, (200, 0, 0))
    sub    = sub_font.render("Click to return to the loading screen.", True, (180, 180, 180))
    screen.blit(banner, (SCREEN_WIDTH // 2 - banner.get_width() // 2,
                          SCREEN_HEIGHT // 2 - banner.get_height()))
    screen.blit(sub,    (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                          SCREEN_HEIGHT // 2 + 20))
    pygame.display.flip()
    # Wait for click
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit(0)
            if event.type == pygame.MOUSEBUTTONDOWN:
                play_positive_click()
                waiting = False
        await asyncio.sleep(0)

async def team_status(team, screen, font):
    deaths = 0
    for member in team:
        if member.current_health <= 0:
            deaths += 1

    for member in team:
        member.demoralize(5 * deaths)

    advance_text_y(20)
    for member in team:
        max_hp  = member.stats["max_health"] if not member.is_robot() else member.max_life
        percent = member.current_health * 100 // max_hp if max_hp > 0 else 0
        color = GREEN
        if percent <= 50:
            color = RED
        emit_team_status_portrait(member, screen, size=50)
        if member.current_health > 0:
            await type_out_text(screen, f"{member.name}  health {percent}%  morale {member.morale}%", font, color)
        else:
            await type_out_text(screen, f"{member.name} is dead.", font, RED)
        advance_text_y(30)

    reset_x_offset()

async def team_repairs_robots(team, screen, font):
    # Check if any robot item hp is below normal
    repair_needed = False
    robots = [m for m in team if m.type == "robot"]
    for robot in robots:
        if robot.type == "robot":
          if 0 < robot.current_health < .75 * robot.max_life:
            await type_out_text(screen, f"{robot.name} needs repair.", font)
            repair_needed = True

    if not repair_needed:
        await type_out_text(screen, "No robot repairs needed.", font)
        return

    # Perform skill check for "Robot Repair"
    repair_successful = team_skill_check(team, "Robot Repair", 0)
    if repair_successful:
        await type_out_text(screen, "Repair skills and equipment improved the results.", font)
        base_repair = 40
    else:
        base_repair = 10

    for robot in robots:
        if robot.type == "robot":
          robot.current_health = min(robot.max_life, robot.current_health + base_repair)
          # Robot morale = health ratio - update after repair
          robot.morale_from_health()

    return

def _select_spare_weapon_to_pass(donor):
    """Return one weapon Item from donor (who has >= 2 weapons) that donor
    would not select to use (or their secondary weapon if carrying 1 ranged + 1 melee)."""
    weapons = [item for item in donor.equipment if item.type == "weapon"]
    if len(weapons) < 2:
        return None
    chosen_ranged = donor.choose_ranged_weapon()
    chosen_melee = donor.choose_melee_weapon()
    unselected = [
        w for w in weapons
        if w is not chosen_ranged and w is not chosen_melee
    ]
    if unselected:
        return min(unselected, key=lambda w: w.effect * w.rate)

    # Donor has 1 ranged weapon and 1 melee weapon; keep the one matching their
    # stronger combat specialization (defaulting to keeping ranged on ties).
    ranged_skills = ("Sharpshooting", "Energy Weapons", "Sonic Weapons", "Projectile Weapons")
    best_ranged_skill = max(
        (donor.get_effective_skill_level(s, learning=False) for s in ranged_skills),
        default=0,
    )
    melee_skill = donor.get_effective_skill_level("Martial Arts", learning=False)
    if melee_skill > best_ranged_skill and chosen_ranged is not None:
        return chosen_ranged
    if chosen_melee is not None:
        return chosen_melee
    return min(weapons, key=lambda w: w.effect * w.rate)


async def share_spare_weapons(team, screen=None, font=None):
    """If one living non-robot character has no weapon and another has 2+ weapons,
    pass one spare weapon (one the donor would not select to use) to the empty-handed member."""
    unarmed = next(
        (m for m in team if m.is_alive() and not m.is_robot() and m.get_weapon_count() == 0),
        None,
    )
    if unarmed is None:
        return None
    donor = next(
        (m for m in team if m is not unarmed and m.is_alive() and not m.is_robot() and m.get_weapon_count() >= 2),
        None,
    )
    if donor is None:
        return None
    spare = _select_spare_weapon_to_pass(donor)
    if spare is None:
        return None
    donor.equipment.remove(spare)
    unarmed.equipment.append(spare)
    if screen is not None and font is not None:
        await type_out_text(
            screen,
            f"{donor.name} passes a spare {spare.name} to the unarmed {unarmed.name}.",
            font,
            CYAN,
        )
    return spare


async def team_heals(team, screen, font):
    # take out your dead
    for member in team[:]:
        if member.current_health <= 0:
            await type_out_text(screen, f"{member.name} is dead.", font, RED)
            team.remove(member)
    # Refresh each survivor's team reference so mulebot checks stay accurate
    for member in team:
        member.team = team

    await share_spare_weapons(team, screen, font)

    healing_needed = team_needs_heal(team)
    if not healing_needed:
        await type_out_text(screen, "No healing is needed.", font)
        return  # No healing needed

    await type_out_text(screen, "The team pauses to heal.", font)

    # Perform skill checks for "Medicine" with difficulty_modifier=0
    # It's okay to skill check against dead members, b/c that check always returns False
    healing_successful = team_skill_check(team, "Medicine", 0)

    # Find the best medikit carried by any team member
    best_medikit = None
    for member in team:
        for item in member.equipment:
            if item_base_name(item.name) == "medikit":
                if best_medikit is None or item.effect > best_medikit.effect:
                    best_medikit = item

    # Determine base healing amounts
    if healing_successful:
        await type_out_text(screen, "Medical skills improved the results.", font)
        base_heal = 50
        medikit_heal = best_medikit.effect if best_medikit else 0
    else:
        base_heal = 25
        medikit_heal = (best_medikit.effect // 2) if best_medikit else 0

    # Check if a medikit is available
    has_medikit = best_medikit is not None or team_has_item(team, "medibot")

    # Remove one medikit if available
    if has_medikit:
        await type_out_text(screen, "A medikit had to be consumed to patch everyone up.", font)
        for member in team:
            for item in member.equipment:
                if item_base_name(item.name) == "medikit":
                    member.equipment.remove(item)
                    break
            else:
                continue
            break

    # Heal all ALIVE team members
    heal_amount = base_heal + (medikit_heal if has_medikit else 0)
    heal_team_by(team, heal_amount)

    await team_status(team, screen, font)

async def calculate_outcome_found_items(team, stat_name, skill_name, screen, font):
    """Outcome for the 'found items' event. Finds one useful unkeyed item for a
    team member (gap-fill or tier upgrade) and grants it to them."""
    from Item import load_items, item_base_name, replace_item_in_inventory
    all_items = load_items()
    await type_out_text(screen, "The team roots around for useful unkeyed items.", font)
    result = get_needed_item(team, all_items)
    if result is None:
        await type_out_text(screen, "The team finds nothing of value.", font)
        return
    recipient, item = result
    old_item = recipient.get_item(item_base_name(item.name))
    if old_item is not None:
        # Upgrade path: swap out the old tier
        replace_item_in_inventory(recipient, old_item, item)
        await type_out_text(
            screen,
            f"Among the supplies, {recipient.name} finds a superior {item.name} and swaps out their old gear.",
            font, GREEN
        )
    else:
        # Gap-fill: character had nothing of this type
        recipient.equipment.append(item)
        await type_out_text(
            screen,
            f"{recipient.name} finds a {item.name} \u2014 exactly what they needed.",
            font, GREEN
        )

def _apply_loop_scaling(enemy, loop=1):
    """Gently scale enemy stats for loop >= 2."""
    if not loop or loop <= 1:
        return enemy
    stat_bonus = min(25, (loop - 1) * 5)
    hp_bonus = min(60, (loop - 1) * 12)
    for st in ("offense", "defense", "meleecombat", "strength", "coordination"):
        if st in enemy.stats:
            enemy.stats[st] = min(140, enemy.stats[st] + stat_bonus)
    enemy.stats["max_health"] = enemy.stats.get("max_health", 100) + hp_bonus
    enemy.current_health = enemy.stats["max_health"]
    return enemy


def pirate_enemies(num_pirates, items, loop=1):
    pirates = []

    # Filter weapons from items where type is "wep"
    weapon_items = [item for item in items.values() if item.type == "weapon"]
    armor_items = [item for item in items.values() if item.type == "armor"]
    non_weapon_items = [item for item in items.values() if (item.type != "weapon" and item.type != "armor")]

    for i in range(num_pirates):
        pirates.append(_apply_loop_scaling(pirate_enemy(i, weapon_items, armor_items, non_weapon_items, items), loop))

    return pirates


def klackon_enemy(i, weapon_items, armor_items, non_weapon_items, all_items, loop=1):
    portrait_idx = (i % 3) + 1
    klackon = Character(portrait_idx, "klackon", 60, 70)
    klackon.index = i
    klackon.name = f"Klackon {i + 1}"

    # Klackons favor fierce melee weapons (slicer / stun baton) and natural chitin armor
    melee_pool = [
        w for w in weapon_items
        if item_base_name(w.name) in ("slicer", "stun baton")
    ] or weapon_items
    ranged_pool = [
        w for w in weapon_items
        if item_base_name(w.name) in ("blaster rifle", "stunner", "laser pistol")
    ]
    if melee_pool:
        klackon.add_item(random.choice(melee_pool))
    if ranged_pool and random.random() < 0.45:
        klackon.add_item(random.choice(ranged_pool))

    heavy_armor_pool = [
        a for a in armor_items
        if item_base_name(a.name) in ("exoskeleton", "powered armor", "veer suit")
    ] or armor_items
    if heavy_armor_pool:
        klackon.add_item(random.choice(heavy_armor_pool))

    return _apply_loop_scaling(klackon, loop)


def klackon_queen(items, loop=2):
    queen = Character(1, "klackon", 60, 70)
    queen.occupation = "klackon"
    queen.name = "Xylarx"
    for item_key in ("slicer S", "blaster rifle A", "powered armor A", "offense implant C"):
        if item_key in items:
            queen.add_item(items[item_key])
    return _apply_loop_scaling(queen, max(2, loop))


def mission_enemies(num_enemies, items, theatre="pirates", loop=1):
    """Spawn enemies appropriate for the mission theatre ('pirates' or 'derelict') with loop scaling."""
    if theatre == "derelict":
        weapon_items = [item for item in items.values() if item.type == "weapon"]
        armor_items = [item for item in items.values() if item.type == "armor"]
        non_weapon_items = [item for item in items.values() if (item.type != "weapon" and item.type != "armor")]
        return [
            klackon_enemy(i, weapon_items, armor_items, non_weapon_items, items, loop=loop)
            for i in range(num_enemies)
        ]
    return pirate_enemies(num_enemies, items, loop=loop)


def jalorith(items):
    pirate = Character(20, "pirate")
    pirate.occupation = "pirate"  # Override occupation to "pirate"
    pirate.name = "Jalorith"

    # Assign a random weapon
    pirate.add_item(items["laser rifle A"])
    pirate.add_item(items["powered armor A"])
    pirate.add_item(items["offense implant C"])
    pirate.add_item(items["slicer S"])
    return pirate

def pirate_enemy(i, weapon_items, armor_items, non_weapon_items, all_items):
    index = random.randint(1, 24)
    pirate = Character(index, "pirate", 60, 70)
    pirate.index = i

    # Assign a random weapon
    if weapon_items:
        weapon = random.choice(weapon_items)
        pirate.add_item(weapon)
        #pirate.add_item(all_items["pistol"])
    if armor_items:
        armor = random.choice(armor_items)
        pirate.add_item(armor)

    # Assign 1-3 random additional items
    num_additional_items = random.randint(1, 3)
    additional_items = random.sample(non_weapon_items, k=min(num_additional_items, len(non_weapon_items)))

    for item in additional_items:
        pirate.add_item(item)
    return pirate

async def pause_to_clear_screen(screen, background, font):
    paused = True
    await type_out_text(screen, "Click to continue.", font)
    while paused:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                play_positive_click()
                paused = False
        await asyncio.sleep(0)   # yield to browser while waiting for click
    clear_screen(screen, background)

class Event:
    def __init__(self, pre_description, post_description, num_enemies, stat_name, skill_name, location, calculate_outcome, all_items, name=None, is_goal=False):
        self.name = name
        self.context = EventContext(pre_description, post_description, num_enemies, stat_name, skill_name, location, calculate_outcome, all_items, name=name, is_goal=is_goal)

    async def run(self, team, screen, font, background, location_font):
        self.context.add_run_params(team, screen, font, background, location_font)
        theatre = (
            team[0].mission.get("theatre", "pirates")
            if team and getattr(team[0], "mission", None)
            else "pirates"
        )
        loop = (
            team[0].mission.get("loop", 1)
            if team and getattr(team[0], "mission", None)
            else 1
        )
        loc_name = getattr(self.context.location, "name", None)
        if self.context.num_enemies == 0:
            self.context.enemies = None
        elif self.context.num_enemies == 6 and loc_name == "officer's quarters":
            enemies = mission_enemies(5, self.context.all_items, theatre="pirates", loop=loop)
            enemies.append(_apply_loop_scaling(jalorith(self.context.all_items), loop))
            self.context.enemies = enemies
        elif self.context.num_enemies == 6 and loc_name == "throneroom":
            enemies = mission_enemies(5, self.context.all_items, theatre="derelict", loop=loop)
            enemies.append(klackon_queen(self.context.all_items, loop=loop))
            self.context.enemies = enemies
        else:
            self.context.enemies = mission_enemies(
                self.context.num_enemies, self.context.all_items, theatre=theatre, loop=loop
            )

        # Display the pre-battle description
        await type_out_text(screen, self.context.pre_description, font)

        # Run the battle, if any
        evaded = False
        if self.context.enemies:
            evaded = await self.run_battle()

        if evaded:
            reset_x_offset()
            await type_out_text(screen, "The enemies were avoided.", font)
            await type_out_text(screen, "Click to proceed.", font)
            return

        # If the team died during battle, mission_failure() already handled the click — stop here
        if team_dead(team):
            return

        # Calculate the outcome of the event
        next_event = await self.context.calculate_outcome(team, self.context.stat_name, self.context.skill_name, screen, font)
        compound_event = False
        # Handle compound events
        while(next_event) is not None:
            compound_event = True
            next_event = await next_event.run(team, screen, font, background, location_font)
            await asyncio.sleep(0)  # yield to browser in compound event chain

        # Don't ask for click on compound events
        reset_x_offset()
        if not compound_event:
            await type_out_text(screen, "Click to proceed.", font)

    async def run_battle(self):
        methods = self.context.team[0].mission.get("methods") if self.context.team and getattr(self.context.team[0], "mission", None) else None
        mission_index = self.context.team[0].mission.get("mission_index") if self.context.team and getattr(self.context.team[0], "mission", None) else None

        # --- Stealth check (skipped for mission_index == 4 where defeating 20 hostiles IS the objective) ---
        if methods == "stealth" and not self.context.is_goal and mission_index != 4:
            if team_evades_notice(self.context.team):
                await type_out_text(self.context.screen, "The team moves silently past the enemies undetected.", self.context.font)
                return True  # evaded — caller skips calculate_outcome
            else:
                await type_out_text(self.context.screen, "The team is spotted! Combat ensues.", self.context.font)
        await type_out_text(self.context.screen, random.choice(enemies_present_statements), self.context.font)

        if methods == "brazen":
            self.context.brazen_bonus = 10
            await type_out_text(self.context.screen, "The team catches the enemy by surprise!", self.context.font)
        await pause_to_clear_screen(self.context.screen, self.context.background, self.context.font)
        event_battle = TeamBattle(self.context)
        await event_battle.run_battle()
        pygame.mixer.music.fadeout(1000)
        await asyncio.sleep(1.5)  # browser Web Audio API fades slower than native; extra buffer
        play_background_music("music/track3.ogg", pygame)
        max_y_offset()

        # If team died, show failure screen and exit — don't heal or continue
        if team_dead(self.context.team):
            await mission_failure(self.context.screen, self.context.font)
            return
        else:
            await pause_to_clear_screen(self.context.screen, self.context.background, self.context.font)

        new_defeated = 0
        if self.context.enemies and self.context.team:
            defeated_now = sum(1 for e in self.context.enemies if not e.is_alive())
            prev_defeated = (
                self.context.team[0].mission.get("enemies_defeated", 0)
                if getattr(self.context.team[0], "mission", None)
                else 0
            )
            new_defeated = prev_defeated + defeated_now
            add_team_mission_param(self.context.team, "enemies_defeated", new_defeated)

        # Heal if appropriate
        if self.context.enemies:
            await team_heals(self.context.team, self.context.screen, self.context.font)
            await team_repairs_robots(self.context.team, self.context.screen, self.context.font)

        # Display the post-battle description
        if self.context.post_description is not None:
            await type_out_text(self.context.screen, self.context.post_description, self.context.font)
        if mission_index == 4 and self.context.enemies:
            await type_out_text(
                self.context.screen,
                f"Mission progress: {min(20, new_defeated)} / 20 hostiles defeated.",
                self.context.font,
                CYAN,
            )
        return False  # not evaded
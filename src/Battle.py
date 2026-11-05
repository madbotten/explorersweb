import asyncio

from enum import Enum

class BattleAction(Enum):
    NONE = 0
    SHOOT = 1
    MELEE = 2
    EVADE = 3
    ITEM = 4
    CHARGE = 5

from TypeText import max_y_offset
from Utils import *
from Character import *
from Item import *
from Location import *
from constants import DEBUG


FLASH_DURATION = 500
CHARACTER_COMBAT_WIDTH = 60
CHARACTER_COMBAT_HEIGHT = 70
ITEM_COMBAT_WIDTH = 40
ITEM_COMBAT_HEIGHT = 40
ROUND_AND_PHASE_LEFT = 30
ACTION_LEFT = 300
TEAM_LEFT = 30
TEAM_RIGHT = 880
TEAM_TOP = 5
TEAM_ACTIONS_X_OFFSET = 300

async def clear_announce_bar(surface):
    background_surface = pygame.Surface((800, 25))
    background_surface.fill((0, 0, 0))
    surface.blit(background_surface, (ROUND_AND_PHASE_LEFT, 5))
    pygame.display.flip()
    await asyncio.sleep(0.5)

def announce_round_and_phase(round, phase, surface, font):
    text = f"Round: {round} Phase: {phase}"
    action_text_surface = font.render(text, True, CYAN)
    background_surface = pygame.Surface((action_text_surface.get_width() + 300, action_text_surface.get_height() + 5))
    background_surface.fill((0, 0, 0))  # Black background
    background_position = (ROUND_AND_PHASE_LEFT, 5)
    surface.blit(background_surface, background_position)
    surface.blit(action_text_surface, (ROUND_AND_PHASE_LEFT, 5))

async def announce_action(text, surface, font):
    action_text_surface = font.render(text, True, CYAN)
    background_surface = pygame.Surface((action_text_surface.get_width() + 150, action_text_surface.get_height() + 5))
    background_surface.fill((0, 0, 0))  # Black background
    background_position = (ACTION_LEFT, 5)
    surface.blit(background_surface, background_position)
    surface.blit(action_text_surface, (ACTION_LEFT, 5))
    pygame.display.flip()
    await asyncio.sleep(0.7)

async def clear_screen_for_round(round, phase, screen, font):
    background_surface = pygame.Surface((500, 800))
    background_surface.fill((0, 0, 0))  # Black background
    background_position = (330, 60)
    screen.blit(background_surface, background_position)
    announce_round_and_phase(round, phase, screen, font)
    pygame.display.flip()
    await asyncio.sleep(0.6)

def _command_tactics_score(member) -> float:
    """Return tactical command bonus from *member*: max(Squad Tactics, Military Science) / 10 + leadership / 30."""
    if member is None or not member.is_alive() or member.is_robot():
        return 0.0
    tactics = max(
        member.get_effective_skill_level("Squad Tactics"),
        member.get_effective_skill_level("Military Science"),
    )
    leadership = member.get_effective_stat_level("leadership")
    return (tactics / 10.0) + (leadership / 30.0)


def initiative(team, enemies, brazen_bonus=0, round_num=1):
    all_characters = team + enemies

    # Calculate scout bonus for the team (+15 if scoutbot is Point Man, else +5)
    scout_bonus = sum(
        15 if getattr(member, "position", None) == "point_man" else 5
        for member in team
        if member.is_alive() and member.occupation == "scoutbot"
    )

    # Calculate command / squad tactics bonus for the team
    has_command_roles = any(
        getattr(m, "command_role", None) in ("commander", "exec") for m in team
    )
    if has_command_roles:
        cmd = next(
            (
                m for m in team
                if m.is_alive()
                and not m.is_robot()
                and getattr(m, "command_role", None) == "commander"
            ),
            None,
        )
        xo = next(
            (
                m for m in team
                if m.is_alive()
                and not m.is_robot()
                and getattr(m, "command_role", None) == "exec"
            ),
            None,
        )
        if cmd is not None:
            squad_tactics_bonus = _command_tactics_score(cmd) + (
                0.5 * _command_tactics_score(xo) if xo is not None else 0.0
            )
        elif xo is not None:
            squad_tactics_bonus = _command_tactics_score(xo)
        else:
            fallback_leader = get_active_commander(team)
            squad_tactics_bonus = _command_tactics_score(fallback_leader)
    else:
        member = determine_best_team_member(team, None, "Squad Tactics")
        if member:
            squad_tactics_bonus = member.get_effective_skill_level("Squad Tactics") / 10
        else:
            squad_tactics_bonus = 0

    # Round 1 no-Point-Man penalty (-10) if the team has formation positions assigned
    # but no living team member occupies Point Man
    has_formation = any(getattr(m, "position", None) is not None for m in team)
    has_living_point_man = any(
        m.is_alive() and getattr(m, "position", None) == "point_man" for m in team
    )
    no_point_penalty = -10 if (round_num == 1 and has_formation and not has_living_point_man) else 0

    # Calculate initiative roll for each character
    initiative_rolls = []
    for character in all_characters:
        roll = random.randint(1, 100) + character.get_effective_stat_level("surprise")
        if character in team:
            roll += scout_bonus
            roll += squad_tactics_bonus
            roll += brazen_bonus  # bonus when team chose "Be brazen"
            roll += no_point_penalty
            if character.is_alive() and getattr(character, "position", None) == "point_man":
                roll += 20
        initiative_rolls.append((character, roll))

    # Sort characters by initiative rolls (highest to lowest)
    initiative_rolls.sort(key=lambda x: x[1], reverse=True)

    # Return sorted characters
    return [entry[0] for entry in initiative_rolls]

# Weapon-base sets used by the phase-specific initiative functions
_RANGED_INITIATIVE_BASES = {"blaster rifle", "laser rifle", "laser pistol",
                             "carbine", "magnum", "pistol", "stunner"}
_MELEE_INITIATIVE_BASES = {"slicer", "stun baton"}

def _best_weapon_rate(character, phase: str) -> int:
    """Return the rate of the character's pre-chosen weapon for *phase*
    ('ranged' or 'melee').  Returns 1 if no weapon was chosen."""
    item = (character.chosen_ranged_weapon if phase == "ranged"
            else character.chosen_melee_weapon)
    return item.rate if item is not None else 1

def initiative_ranged(team, enemies, brazen_bonus=0, round_num=1) -> list:
    """Build the ranged-phase action list.

    The base initiative order is computed first.  Then, for each extra shot
    level (2 … 5), every character whose chosen ranged weapon has rate ≥ that
    level is appended again in base-order.  Characters with rate 1 appear
    once; rate 2 twice; rate 5 five times.
    """
    base = initiative(team, enemies, brazen_bonus, round_num=round_num)
    extended = list(base)
    for shot in range(2, 6):
        for character in base:
            if _best_weapon_rate(character, "ranged") >= shot:
                extended.append(character)
    return extended

def initiative_melee(team, enemies, brazen_bonus=0, round_num=1) -> list:
    """Build the melee-phase action list using the character's chosen melee weapon rate."""
    base = initiative(team, enemies, brazen_bonus, round_num=round_num)
    extended = list(base)
    for shot in range(2, 6):
        for character in base:
            if _best_weapon_rate(character, "melee") >= shot:
                extended.append(character)
    return extended

def battle_display_character(character, context, xloc, yloc):
    character.set_rect(pygame.Rect(xloc, yloc, CHARACTER_COMBAT_WIDTH, CHARACTER_COMBAT_HEIGHT))
    context.screen.blit(character.portrait, character.get_rect())
    text_surface = context.font.render(character.name, True, GREEN)
    context.screen.blit(text_surface, (xloc + 70, yloc + CHARACTER_COMBAT_HEIGHT - 18))
    draw_life_bar(character, context.screen, xloc, yloc)
    offset = 70
    for item in character.equipment: # convert to type once armor is a type
        # simplify: Item needs a bit for "combat display item"
        if item.type == "weapon" or item.type == "armor":
            item.set_rect(pygame.Rect(xloc + offset, yloc, ITEM_COMBAT_WIDTH, ITEM_COMBAT_HEIGHT))
            context.screen.blit(item.icon, (xloc + offset, yloc))
            offset += 45
    draw_character_location_dot(character, context)

def draw_character_location_dot(character, context):
    color = GREEN
    if character.is_pirate():
        color = RED
        if character.location == (-1, -1):
            character.location = (random.randint(-5, 5), random.randint(1, 10))
            if context.location.name == "corridor":
                character.location = (random.randint(-2, 2), random.randint(1, 10))
        character.location = (LOCATION_NORTH[0] + character.location[0] * 10, LOCATION_NORTH[1] + character.location[1] * 10)
    else:
        if character.location == (-1, -1):
            character.location = (random.randint(-5, 5), random.randint(1, 10))
            if context.location.name == "corridor":
                character.location = (random.randint(-2, 2), random.randint(1, 10))
        character.location = (LOCATION_SOUTH[0] + character.location[0] * 10, LOCATION_SOUTH[1] - character.location[1] * 10)
    draw_numbered_dot(character, context, color)

def draw_numbered_dot(character, context, color):
    pygame.draw.circle(context.screen, color, character.location, 7)
    text_surface = context.font.render(str(character.battle_index), True, BLACK)
    if character.battle_index == 1:
        context.screen.blit(text_surface, (character.location[0] - 3, character.location[1] - 6))
    elif character.battle_index > 9:
        context.screen.blit(text_surface, (character.location[0] - 5, character.location[1] - 6))
    else:
        context.screen.blit(text_surface, (character.location[0] - 4, character.location[1] - 6))

def draw_life_bar(character, screen, x, y):
    # Calculate life level proportion
    current_life = character.get_lifelevel()
    max_life = character.get_max_health()
    # limit bar size for screen constraints
    max_life = min(200, max_life)

    # Background bar (gray)
    background_rect = pygame.Rect(x + 70, y + 46, max_life, 5)
    pygame.draw.rect(screen, (60, 60, 60), background_rect)

    # Foreground bar (green)
    foreground_rect = pygame.Rect(x + 70, y + 46, current_life, 5)
    pygame.draw.rect(screen, (0, 255, 0), foreground_rect)

# Width of the strip cleared for action + HIT/MISS + damage labels
ACTION_CLEAR_WIDTH = 200

def clear_character_action_area(character, screen):
    """Black out the action-text row next to this character's portrait."""
    row_h = font_height = 24  # tall enough to cover a 16-pt Orbitron label
    y = character.get_rect().top
    if character.is_pirate():
        x = character.get_rect().left - TEAM_ACTIONS_X_OFFSET
    else:
        x = character.get_rect().left + TEAM_ACTIONS_X_OFFSET
    clear_surf = pygame.Surface((ACTION_CLEAR_WIDTH, row_h))
    clear_surf.fill((0, 0, 0))
    screen.blit(clear_surf, (x, y))

def battle_display_action(character, action, screen, font):
    clear_character_action_area(character, screen)
    if character.is_pirate():
        battle_display_pirate_action(character, action, screen, font)
    else:
        battle_display_character_action(character, action, screen, font)

def battle_display_character_action(character, action, screen, font):
    text_surface = font.render(action.name, True, GREEN)
    screen.blit(text_surface, (character.get_rect().left + TEAM_ACTIONS_X_OFFSET, character.get_rect().top))
    pygame.display.flip()

def battle_display_pirate_action(character, action, screen, font):
    text_surface = font.render(action.name, True, GREEN)
    screen.blit(text_surface, (character.get_rect().left - TEAM_ACTIONS_X_OFFSET, character.get_rect().top))
    pygame.display.flip()

async def battle_display_character_hit(character, screen):
    red_overlay = pygame.Surface(character.portrait.get_size(), pygame.SRCALPHA)
    red_overlay.fill((255, 0, 0, 128))  # Semi-transparent red
    screen.blit(red_overlay, character.rect)
    pygame.display.flip()
    await asyncio.sleep(.5)
    screen.blit(character.portrait, character.rect)
    pygame.display.flip()

def battle_display_character_action_result(character, action, hit, screen, font):
    color = RED
    result = "MISS"
    if hit:
        color = GREEN
        result = "HIT"
    text_surface = font.render(result, True, color)
    screen.blit(text_surface, (character.get_rect().left + TEAM_ACTIONS_X_OFFSET + 70, character.get_rect().top))

def battle_display_pirate_action_result(character, action, hit, screen, font):
    color = RED
    result = "MISS"
    if hit:
        color = GREEN
        result = "HIT"
    text_surface = font.render(result, True, color)
    screen.blit(text_surface, (character.get_rect().left - TEAM_ACTIONS_X_OFFSET + 70, character.get_rect().top))

def battle_display_action_damage(character, action, hit, screen, font):
    if character.is_pirate():
        battle_display_pirate_action_damage(character, action, hit, screen, font)
    else:
        battle_display_character_action_damage(character, action, hit, screen, font)

def battle_display_character_action_damage(character, action, damage, screen, font):
    color = RED
    text_surface = font.render(str(damage), True, color)
    screen.blit(text_surface, (character.get_rect().left + TEAM_ACTIONS_X_OFFSET + 110, character.get_rect().top))

def battle_display_pirate_action_damage(character, action, damage, screen, font):
    color = RED
    text_surface = font.render(str(damage), True, color)
    screen.blit(text_surface, (character.get_rect().left - TEAM_ACTIONS_X_OFFSET + 110, character.get_rect().top))

class TeamBattle:
    def __init__(self, context):
        self.context = context
        self.smaller_font = pygame.font.Font(resource_path("fonts/Orbitron-Bold.ttf"), 12)
        self.smallest_font = pygame.font.Font(resource_path("fonts/Orbitron-Bold.ttf"), 9)
        for member in context.team:
            member.location = (-1, -1)
        if context.enemies:
            for member in context.enemies:
                member.location = (-1, -1)
        self.round = 1

    def draw_teams(self):
        offset = TEAM_TOP
        index = 1
        for member in self.context.team:
            if member.is_alive():
                member.set_rect(pygame.Rect(TEAM_LEFT, 50 + offset, CHARACTER_COMBAT_WIDTH, CHARACTER_COMBAT_HEIGHT))
                member.battle_index = index
                battle_display_character(member, self.context, member.rect.left, member.rect.top)
                offset += 75
                index += 1
                self.draw_map_name(member)
        offset = TEAM_TOP
        for member in self.context.enemies:
            if member.is_alive():
                member.set_rect(pygame.Rect(TEAM_RIGHT, 50 + offset, CHARACTER_COMBAT_WIDTH, CHARACTER_COMBAT_HEIGHT))
                member.battle_index = index
                battle_display_character(member, self.context, member.rect.left, member.rect.top)
                offset += 75
                index += 1
                self.draw_map_name(member, RED)

    def draw_map_name(self, member, color=GREEN):
        xloc = LOCATION_LEFT
        yloc = LOCATION_TOP + LOCATION_TOP + LOCATION_HEIGHT + member.battle_index * 20
        draw_numbered_dot(member, self.context, color)
        pygame.draw.circle(self.context.screen, color, (xloc, yloc), 7)
        text_surface = self.smallest_font.render(str(member.battle_index), True, BLACK)
        if member.battle_index == 1:
            self.context.screen.blit(text_surface, (xloc - 3, yloc - 6))
        elif member.battle_index > 9:
            self.context.screen.blit(text_surface, (xloc - 5, yloc - 6))
        else:
            self.context.screen.blit(text_surface, (xloc-4, yloc-6))
        xloc += 10
        yloc -= 8
        text_surface = self.smaller_font.render(member.name, True, color)
        self.context.screen.blit(text_surface, (xloc, yloc))

    def choose_battle_action_ranged_phase(self, member):
        if member.chosen_ranged_weapon is not None:
            return BattleAction.SHOOT
        return BattleAction.EVADE

    def choose_battle_action_melee_phase(self, member):
        if (
            member in self.context.team
            and getattr(member, "position", None) == "overwatch"
            and any(
                m.is_alive() and getattr(m, "position", None) == "center"
                for m in self.context.team
            )
        ):
            return BattleAction.EVADE
        if member.chosen_melee_weapon is not None:
            return BattleAction.MELEE
        return BattleAction.EVADE

    async def run_battle_action(self, character, action):
        if action == BattleAction.MELEE:
            await self.run_battle_action_melee(character)
        elif action == BattleAction.EVADE:
            await self.run_battle_action_evade(character)
        elif action == BattleAction.SHOOT:
            await self.run_battle_action_shoot(character)
        elif action == BattleAction.ITEM:
            self.run_battle_action_item(character)
            return

    def run_battle_action_item(self, character):
        # TODO: implement item usage in combat
        character.last_action = BattleAction.ITEM
        return

    async def run_battle_action_evade(self, character):
        if DEBUG:
            print(f"{character.name} evades.")
        await announce_action(f"{character.name}'s action: EVADE", self.context.screen, self.context.font)
        battle_display_action(character, BattleAction.EVADE, self.context.screen, self.context.font)
        character.last_action = BattleAction.EVADE
        return

    async def run_battle_action_melee(self, character):
        character.last_action = BattleAction.MELEE
        # Choose target logic
        if not character.is_pirate():
            target = self.choose_target(character, self.context.enemies, round_num=self.round, attack_type="melee")
        else:
            target = self.choose_target(character, self.context.team, round_num=self.round, attack_type="melee")
        if target is None:
            print(f"{character.name} Finds no target!")
            return

        # Choose weapon logic
        chosen_weapon = self.choose_melee_weapon(character, target)
        if chosen_weapon is None:
            print(f"{character.name} Finds no weapon!")
            return
        weapon_obj = (
            self.context.all_items.get(chosen_weapon)
            or getattr(character, "chosen_melee_weapon", None)
            or DEFAULT_KNIFE_WEAPON
        )
        base_weapon_effect = weapon_obj.effect
        effect_type = weapon_obj.effect_type

        await announce_action(f"{character.name}'s action: MELEE", self.context.screen, self.context.font)

        # play sound (strip class suffix for sound lookup)
        play_weapon_sound(item_base_name(chosen_weapon), character)

        battle_display_action(character, BattleAction.MELEE, self.context.screen, self.context.font)

        # for loop of weapon rate

        # Calculate if hit, low roll is better
        hit = False
        roll = random.randint(1, 100)
        if roll < 95:
            melee = character.get_effective_combat_melee()
            target_melee = target.get_effective_combat_melee()
            target_evasion = target.get_effective_stat_level("evasion")
            offense = character.get_effective_stat_level("offense")
            
            adjusted_roll = roll
            if target.last_action == BattleAction.EVADE:
                adjusted_roll += 10 + (target_evasion / 10)
            if target.has_item("holofier"):
                holofier_item = target.get_item("holofier")
                adjusted_roll += round(holofier_item.effect * 0.6) if holofier_item else 15
            if character.get_effective_skill_level("Martial Arts", learning=False) > 0:
                adjusted_roll -= 10 + (character.get_effective_skill_level("Martial Arts") / 10)
            if self.round == 1 and not character.is_pirate() and getattr(character, "position", None) == "point_man":
                adjusted_roll -= 15
            if (
                self.round == 1
                and character.is_pirate()
                and getattr(target, "position", None) == "point_man"
                and getattr(target, "occupation", None) == "scoutbot"
            ):
                adjusted_roll += 15
            if (
                character.is_pirate()
                and getattr(target, "position", None) == "center"
                and sum(
                    1
                    for m in (self.context.team or [])
                    if m.is_alive() and getattr(m, "position", None) == "center"
                ) >= 2
            ):
                adjusted_roll += 8
            adjusted_roll = adjusted_roll * target_melee/melee
            if adjusted_roll < offense:
                hit = True

        if not character.is_pirate():
            battle_display_character_action_result(character, BattleAction.MELEE, hit, self.context.screen, self.context.font)
        else:
            battle_display_pirate_action_result(character, BattleAction.MELEE, hit, self.context.screen, self.context.font)
        if hit:
            print(f"Hit on roll {roll}")
        else:
            print(f"Miss on roll {roll}")

        # If hit calculate damage
        adjusted_damage = 0
        # Determine which melee skill applies
        melee_skill = "Sonic Weapons" if effect_type == "sonic" else "Martial Arts"
        if hit:
            adjusted_damage = random.randint(1, base_weapon_effect)
            adjusted_damage = adjusted_damage * (character.get_effective_combat_offense() / target.get_effective_combat_defense())
            if item_base_name(chosen_weapon) != "knife":
                if character.get_effective_skill_level(melee_skill) > 75:
                    adjusted_damage += 20
                elif character.get_effective_skill_level(melee_skill) > 50:
                    adjusted_damage += 10
            adjusted_damage = round(adjusted_damage)
            print(f"Damage is: {adjusted_damage}")

        # Round and apply damage
        adjusted_damage = round(adjusted_damage)
        if hit:
            target.hurt(adjusted_damage, effect_type)
            draw_life_bar(target, self.context.screen, target.rect.left, target.rect.top)
            battle_display_action_damage(character, BattleAction.MELEE, adjusted_damage, self.context.screen, self.context.font)
            await battle_display_character_hit(target, self.context.screen)
        return

    @staticmethod
    def choose_target(character, team, round_num=1, attack_type="ranged"):
        alive = [m for m in team if m.is_alive()]
        if not alive:
            return None

        # Player team attacking enemies: uniform random among living enemies
        if not character.is_pirate():
            target = random_alive_member(alive)
            if target:
                print(f"{character.name} chooses target {target.name}")
            return target

        # Enemy attacking the player's team: apply melee position exclusions first
        if attack_type == "melee":
            has_alive_center = any(getattr(m, "position", None) == "center" for m in alive)
            has_alive_center_or_overwatch = any(
                getattr(m, "position", None) in ("center", "overwatch") for m in alive
            )
            eligible = []
            for m in alive:
                pos = getattr(m, "position", None)
                if pos == "overwatch" and round_num <= 3 and has_alive_center:
                    continue
                if pos == "protected" and has_alive_center_or_overwatch:
                    continue
                eligible.append(m)
            if not eligible:
                eligible = alive
        else:
            eligible = alive

        # Apply position weights (Point Man 3.0x in round 1; Protected 0.25x in rounds 1-3)
        weights = []
        for m in eligible:
            pos = getattr(m, "position", None)
            w = 1.0
            if round_num == 1 and pos == "point_man":
                w = 3.0
            elif round_num <= 3 and pos == "protected":
                w = 0.25
            weights.append(w)

        if all(w == 1.0 for w in weights):
            target = random_alive_member(eligible)
        else:
            target = random.choices(eligible, weights=weights, k=1)[0]

        if target:
            print(f"{character.name} chooses target {target.name}")
        return target

    _RANGED_WEAPON_BASES = {"blaster rifle", "laser rifle", "laser pistol",
                             "carbine", "magnum", "pistol", "stunner"}

    def choose_ranged_weapon(self, character, target):
        """Return the name of the character's pre-chosen ranged weapon."""
        item = character.chosen_ranged_weapon
        return item.name if item else None

    def weapon_is_rifle(self, weapon):
        return item_base_name(weapon) in {"blaster rifle", "laser rifle"}

    _MELEE_WEAPON_BASES = {"slicer", "stun baton"}

    @staticmethod
    def choose_melee_weapon(character, target):
        """Return the name of the character's pre-chosen melee weapon."""
        item = character.chosen_melee_weapon
        return item.name if item else None

    async def run_battle_action_shoot(self, character):
        character.last_action = BattleAction.SHOOT
        # Choose target logic
        if not character.is_pirate():
            target = self.choose_target(character, self.context.enemies, round_num=self.round, attack_type="ranged")
        else:
            target = self.choose_target(character, self.context.team, round_num=self.round, attack_type="ranged")
        if target is None:
            print(f"{character.name} Finds no target!")
            return

        # Choose weapon logic
        chosen_weapon = self.choose_ranged_weapon(character, target)
        if chosen_weapon is None:
            print(f"{character.name} Finds no weapon!")
            return
        base_weapon_effect = self.context.all_items[chosen_weapon].effect
        effect_type = self.context.all_items[chosen_weapon].effect_type

        await announce_action(f"{character.name}'s action: SHOOT", self.context.screen, self.context.font)

        # play sound (strip class suffix for sound lookup)
        play_weapon_sound(item_base_name(chosen_weapon), character)

        battle_display_action(character, BattleAction.SHOOT, self.context.screen, self.context.font)

        # for loop of weapon rate

        # Calculate if hit, lower roll is better
        hit = False
        roll = random.randint(1, 100)
        skill = "Projectile Weapons"
        
        if roll > 3:
            # offense and evasion reflects health status
            offense = character.get_effective_combat_offense()
            target_evasion = target.get_effective_combat_evasion()
            
            adjusted_roll = roll
            if effect_type == "impact":
                skill = "Projectile Weapons"
            elif effect_type == "energy":
                skill = "Energy Weapons"
            elif effect_type == "sonic":
                skill = "Sonic Weapons"

            # if target evades, add 10 + evasion/10 to attacker's ranged roll
            if target.last_action == BattleAction.EVADE:
                adjusted_roll += 10 + (target_evasion / 10)
            # if target has holofier, add its effect value to attacker's ranged roll
            if target.has_item("holofier"):
                holofier_item = target.get_item("holofier")
                adjusted_roll += holofier_item.effect if holofier_item else 25
            adjusted_roll -= character.get_effective_skill_level(skill)/10
            if self.weapon_is_rifle(chosen_weapon):
                adjusted_roll -= character.get_effective_skill_level("Sharpshooting") / 10
            if self.round == 1 and not character.is_pirate() and getattr(character, "position", None) == "point_man":
                adjusted_roll -= 15
            if (
                self.round == 1
                and character.is_pirate()
                and getattr(target, "position", None) == "point_man"
                and getattr(target, "occupation", None) == "scoutbot"
            ):
                adjusted_roll += 15
            if (
                not character.is_pirate()
                and getattr(character, "position", None) == "overwatch"
                and any(
                    m.is_alive() and getattr(m, "position", None) in ("center", "point_man")
                    for m in (self.context.team or [])
                )
            ):
                adjusted_roll -= 8

            adjusted_roll = adjusted_roll * target_evasion / offense
            if adjusted_roll < offense:
                hit = True

        if not character.is_pirate():
            battle_display_character_action_result(character, BattleAction.SHOOT, hit, self.context.screen, self.context.font)
        else:
            battle_display_pirate_action_result(character, BattleAction.SHOOT, hit, self.context.screen, self.context.font)
        if hit:
            print(f"{character.name} hit on roll {roll}")
        else:
            print(f"{character.name} missed on roll {roll}")

        # If hit calculate damage
        adjusted_damage = 0
        if hit:
            adjusted_damage = random.randint(1, base_weapon_effect)
            adjusted_damage = (adjusted_damage *
                               (character.get_effective_combat_offense() / target.get_effective_combat_defense()))
            if character.get_effective_skill_level(skill) > 75:
                adjusted_damage += 20
            elif character.get_effective_skill_level(skill) > 50:
                adjusted_damage += 10
            adjusted_damage = round(adjusted_damage)
            print(f"Damage is: {adjusted_damage}")

        # Round and apply damage
        adjusted_damage = round(adjusted_damage)

        if hit:
            await self.damage_target(character, target, adjusted_damage, effect_type, self.context.screen, self.context.font)
        return

    @staticmethod
    async def damage_target(character, target, adjusted_damage, effect_type, screen, font):
        target.hurt(adjusted_damage, effect_type)
        draw_life_bar(target, screen, target.rect.left, target.rect.top)
        battle_display_action_damage(character, BattleAction.SHOOT, adjusted_damage, screen, font)
        await battle_display_character_hit(target, screen)

    def battle_ended(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit(0)

        if not team_alive(self.context.team):
            return True
        if not team_alive(self.context.enemies):
            return True
        return False

    async def check_battle_ended(self):
        await asyncio.sleep(0)  # yield to browser between rounds
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit(0)

        if not team_alive(self.context.team):
            max_y_offset()
            await clear_announce_bar(self.context.screen)
            await announce_action("Team is dead!", self.context.screen, self.context.font)
            return False
        if not team_alive(self.context.enemies):
            max_y_offset()
            await clear_announce_bar(self.context.screen)
            await announce_action("Enemies defeated.", self.context.screen, self.context.font)
            return False
        return True

    def _prepare_weapons(self):
        """Pre-select each combatant's ranged and melee weapon for this battle.
        Called once at the start of run_battle before any initiative rolls.
        """
        for character in self.context.team + self.context.enemies:
            character.chosen_ranged_weapon = character.choose_ranged_weapon()
            character.chosen_melee_weapon  = character.choose_melee_weapon()

    async def run_battle(self):
        try:
            import platform
            platform.window.console.log("battle: starting run_battle")
        except Exception:
            pass
        await clear_announce_bar(self.context.screen)
        pygame.mixer.music.fadeout(1000)
        await asyncio.sleep(1.5)  # browser Web Audio API fades slower than native; extra buffer
        try:
            import platform
            platform.window.console.log("battle: calling play_battle_music")
        except Exception:
            pass
        play_battle_music(pygame)
        try:
            import platform
            platform.window.console.log("battle: play_battle_music done, drawing location")
        except Exception:
            pass
        draw_location(self.context.location, self.context.screen, LOCATION_LEFT, LOCATION_TOP, self.context.location_font, self.smaller_font)
        self.draw_teams()
        pygame.display.flip()
        await asyncio.sleep(0.5)
        self._prepare_weapons()
        try:
            import platform
            platform.window.console.log("battle: weapons prepared, starting battle loop")
        except Exception:
            pass
        battle_rages = True
        self.round = 1
        while battle_rages:
            await asyncio.sleep(0)  # yield to browser at start of each round
            await clear_screen_for_round(self.round, "RANGED", self.context.screen, self.context.font)
            # RANGED PHASE — initiative includes extra shots from weapon rate
            ranged_order = initiative_ranged(self.context.team, self.context.enemies, getattr(self.context, "brazen_bonus", 0), round_num=self.round)
            for character in ranged_order:
                await asyncio.sleep(0)  # yield to browser for each character action
                if character.is_alive():
                    action = self.choose_battle_action_ranged_phase(character)
                    character.last_action = action
                    await self.run_battle_action(character, action)
            await asyncio.sleep(0.8)

            # MELEE PHASE — own initiative roll
            if not self.battle_ended():
                await clear_screen_for_round(self.round, "MELEE", self.context.screen, self.context.font)
                await asyncio.sleep(0.8)
                melee_order = initiative_melee(self.context.team, self.context.enemies, getattr(self.context, "brazen_bonus", 0), round_num=self.round)
                for character in melee_order:
                    await asyncio.sleep(0)  # yield to browser for each character action
                    if character.is_alive():
                        action = self.choose_battle_action_melee_phase(character)
                        await self.run_battle_action(character, action)

            battle_rages = await self.check_battle_ended()
            self.round += 1
        # click to continue...
        await asyncio.sleep(1)
        max_y_offset()
        clear_team_last_action(self.context.team)
        return

    async def print_debug(self, round):
        if DEBUG:
            print(str(round))
        for member in self.context.team:
            print(f"{member.name} : life: {member.get_lifelevel()}")
        for member in self.context.enemies:
            print(f"{member.name} : life: {member.get_lifelevel()}")
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit(0)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    return
            await asyncio.sleep(0)  # yield to browser while waiting for debug click


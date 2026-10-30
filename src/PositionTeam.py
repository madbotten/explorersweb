import asyncio
import pygame

from Character import Character
from Utils import (
    WHITE,
    BLACK,
    RED,
    GREEN,
    CYAN,
    DARK_CYAN,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    color_for_stat,
    color_for_skill,
    resource_path,
    play_background_music,
    save_team_named,
    load_team_named,
)
from constants import TOP_BAR_Y, DEBUG

# ---------------------------------------------------------------------------
# Role and formation constants
# ---------------------------------------------------------------------------
ROLE_COMMANDER = "commander"
ROLE_EXEC = "exec"
COMMAND_ROLES = (ROLE_COMMANDER, ROLE_EXEC)

POS_POINT_MAN = "point_man"
POS_CENTER = "center"
POS_OVERWATCH = "overwatch"
POS_PROTECTED = "protected"
FORMATION_POSITIONS = (POS_POINT_MAN, POS_CENTER, POS_OVERWATCH, POS_PROTECTED)

ROLE_LABELS = {
    ROLE_COMMANDER: "Mission Commander",
    ROLE_EXEC: "Executive Officer",
}

POSITION_LABELS = {
    POS_POINT_MAN: "Point Man",
    POS_CENTER: "Center",
    POS_OVERWATCH: "Overwatch",
    POS_PROTECTED: "Protected Specialists",
}

# ---------------------------------------------------------------------------
# Layout constants (1500 x 900 screen)
# ---------------------------------------------------------------------------
PORTRAIT_W = 70
PORTRAIT_H = 80

PROCEED_RECT = pygame.Rect(1220, TOP_BAR_Y, 120, 25)
EXIT_RECT = pygame.Rect(1400, TOP_BAR_Y, 90, 25)

LEFT_POOL_RECT = pygame.Rect(20, 55, 235, 825)

COMMANDER_BOX_RECT = pygame.Rect(280, 85, 240, 130)
EXEC_BOX_RECT = pygame.Rect(550, 85, 240, 130)

POINT_MAN_BOX_RECT = pygame.Rect(280, 260, 240, 135)
CENTER_BOX_RECT = pygame.Rect(280, 415, 745, 140)
OVERWATCH_BOX_RECT = pygame.Rect(280, 575, 745, 140)
PROTECTED_BOX_RECT = pygame.Rect(280, 735, 745, 140)

INFO_BOX_RECT = pygame.Rect(1045, 85, 435, 790)

COMMAND_BOX_RECTS = {
    ROLE_COMMANDER: COMMANDER_BOX_RECT,
    ROLE_EXEC: EXEC_BOX_RECT,
}

FORMATION_BOX_RECTS = {
    POS_POINT_MAN: POINT_MAN_BOX_RECT,
    POS_CENTER: CENTER_BOX_RECT,
    POS_OVERWATCH: OVERWATCH_BOX_RECT,
    POS_PROTECTED: PROTECTED_BOX_RECT,
}


# ---------------------------------------------------------------------------
# Pure domain helpers (shared by UI and unit tests)
# ---------------------------------------------------------------------------

def assign_command_role(team: list, character: Character, role: str) -> tuple[bool, str | None]:
    """Assign a character to Mission Commander or Executive Officer.

    - Robots cannot be Mission Commander or Executive Officer.
    - Does not alter character.position (so the icon stays in the left roster
      until placed in a formation box, and appears in both places once placed).
    - If another character holds `role`, swaps or clears their command_role so
      at most one character holds each command role and one character cannot
      hold both roles simultaneously.
    """
    if role not in COMMAND_ROLES:
        return False, f"Invalid command role: {role}"
    if character not in team:
        return False, "Character is not on the team"
    if character.is_robot():
        return False, "Robots cannot be Mission Commander or Exec Officer"

    previous_role = getattr(character, "command_role", None)
    for member in team:
        if member is not character and getattr(member, "command_role", None) == role:
            member.command_role = previous_role

    character.command_role = role
    return True, None


def clear_command_role(character: Character) -> None:
    """Remove any command role assignment from `character`."""
    character.command_role = None


def assign_formation_position(team: list, character: Character, position: str) -> tuple[bool, str | None]:
    """Place a character (human or robot) into one of the 4 movement formation boxes.

    - Point Man accepts only 1 character; if occupied, the previous occupant swaps
      to `character`'s prior formation position (or None, returning to the left pool).
    - Center, Overwatch, and Protected Specialists accept multiple characters.
    """
    if position not in FORMATION_POSITIONS:
        return False, f"Invalid formation position: {position}"
    if character not in team:
        return False, "Character is not on the team"

    previous_pos = getattr(character, "position", None)
    if position == POS_POINT_MAN:
        for member in team:
            if member is not character and getattr(member, "position", None) == POS_POINT_MAN:
                member.position = previous_pos

    character.position = position
    return True, None


def unassign_formation_position(character: Character) -> None:
    """Remove a character from their formation box, returning them to the left pool."""
    character.position = None


def normalize_team_positions(team: list) -> None:
    """Sanitize command roles and formation positions on stage entry."""
    seen_roles = set()
    seen_point_man = False
    for member in team:
        role = getattr(member, "command_role", None)
        if member.is_robot() or role not in COMMAND_ROLES or role in seen_roles:
            member.command_role = None
        else:
            seen_roles.add(role)

        pos = getattr(member, "position", None)
        if pos not in FORMATION_POSITIONS:
            member.position = None
        elif pos == POS_POINT_MAN:
            if seen_point_man:
                member.position = None
            else:
                seen_point_man = True


def can_proceed(team: list) -> bool:
    """Return True when Mission Commander, Executive Officer, and all member
    formation positions are assigned."""
    if not team:
        return False

    commanders = [
        m for m in team
        if not m.is_robot() and getattr(m, "command_role", None) == ROLE_COMMANDER
    ]
    execs = [
        m for m in team
        if not m.is_robot() and getattr(m, "command_role", None) == ROLE_EXEC
    ]
    if len(commanders) != 1 or len(execs) != 1 or commanders[0] is execs[0]:
        return False

    return all(getattr(m, "position", None) in FORMATION_POSITIONS for m in team)


_INSPECT_STATS_ORDER = (
    ("strength", "Strength", 1),
    ("intelligence", "Intelligence", 1),
    ("willpower", "Willpower", 1),
    ("coordination", "Coordination", 1),
    ("charisma", "Charisma", 1),
    ("courage", "Courage", 1),
    ("offense", "Offense", 1),
    ("defense", "Defense", 1),
    ("deception", "Deception", 1),
    ("evasion", "Evasion", 1),
    ("analyze", "Analysis", 1),
    ("max_health", "Max Health", 2),
    ("movement", "Movement", 3),
    ("meleecombat", "Melee", 2),
    ("surprise", "Surprise", 2),
    ("leadership", "Leadership", 3),
    ("perception", "Perception", 1),
)


def get_character_inspection_data(character: Character) -> dict:
    """Return structured stats, skills, and equipment data for the character info box."""
    is_robot = character.is_robot()
    max_hp = (
        character.max_life
        if (is_robot and getattr(character, "max_life", 0) > 0)
        else character.stats.get("max_health", 0)
    )

    stats_list = []
    for stat_key, label, scale in _INSPECT_STATS_ORDER:
        if stat_key in character.stats:
            val = character.stats[stat_key]
            scaled_val = round(val / scale) if scale > 1 else val
            stats_list.append((stat_key, label, val, color_for_stat(scaled_val)))

    skills_dict = getattr(character, "skills", {}) or {}
    skills_list = [
        (skill_name, proficiency, color_for_skill(proficiency))
        for skill_name, proficiency in skills_dict.items()
    ]

    equipment_list = list(getattr(character, "equipment", []) or [])

    return {
        "name": character.name,
        "occupation": getattr(character, "occupation", character.type),
        "is_robot": is_robot,
        "current_health": getattr(character, "current_health", max_hp),
        "max_health": max_hp,
        "morale": getattr(character, "morale", 100),
        "command_role": ROLE_LABELS.get(getattr(character, "command_role", None)),
        "position": POSITION_LABELS.get(getattr(character, "position", None)),
        "stats": stats_list,
        "skills": skills_list,
        "equipment": equipment_list,
    }


# ---------------------------------------------------------------------------
# Pygame stage screen
# ---------------------------------------------------------------------------

async def position_team(team_data, team_name="Debug Team", loop=1):
    if DEBUG:
        print("started position team")

    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Position Your Team")

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 3)
    team = [Character.from_dict(data) for data in team_data]
    for character in team:
        character.team = team
        if getattr(character, "portrait", None):
            character.portrait = pygame.transform.scale(character.portrait, (PORTRAIT_W, PORTRAIT_H))

    normalize_team_positions(team)

    play_background_music("music/track2.mp3", pygame)

    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage2.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    TITLE_FONT = pygame.font.Font(font_path, 18)
    BOX_TITLE_FONT = pygame.font.Font(font_path, 15)
    INFO_FONT = pygame.font.Font(font_path, 13)
    NAME_FONT = pygame.font.Font(font_path, 12)

    EXIT_TEXT = TITLE_FONT.render("EXIT", True, RED)

    stage = 4
    status_message = ""
    status_timer = 0

    # Drag and selection state
    selected_character = None
    dragging_char = None
    dragging_source = None  # ("pool", None) | ("command", role) | ("formation", pos)
    dragging_rect = None

    def set_status(msg: str, frames: int = 120):
        nonlocal status_message, status_timer
        status_message = msg
        status_timer = frames

    def compute_pool_slots():
        """Return [(character, pygame.Rect), ...] for unassigned characters in the left pool."""
        slots = []
        unassigned = [m for m in team if getattr(m, "position", None) is None]
        for idx, member in enumerate(unassigned):
            col = idx % 2
            row = idx // 2
            x = LEFT_POOL_RECT.x + 22 + col * 105
            y = LEFT_POOL_RECT.y + 45 + row * 120
            slots.append((member, pygame.Rect(x, y, PORTRAIT_W, PORTRAIT_H)))
        return slots

    def compute_command_slots():
        """Return {role: (character, pygame.Rect)} for occupied command boxes."""
        slots = {}
        for role, box_rect in COMMAND_BOX_RECTS.items():
            holder = next((m for m in team if getattr(m, "command_role", None) == role), None)
            if holder is not None:
                px = box_rect.centerx - PORTRAIT_W // 2
                py = box_rect.y + 30
                slots[role] = (holder, pygame.Rect(px, py, PORTRAIT_W, PORTRAIT_H))
        return slots

    def compute_formation_slots():
        """Return {pos: [(character, pygame.Rect), ...]} for characters in formation boxes."""
        slots = {pos: [] for pos in FORMATION_POSITIONS}
        for pos, box_rect in FORMATION_BOX_RECTS.items():
            members = [m for m in team if getattr(m, "position", None) == pos]
            if pos == POS_POINT_MAN:
                for m in members[:1]:
                    px = box_rect.centerx - PORTRAIT_W // 2
                    py = box_rect.y + 32
                    slots[pos].append((m, pygame.Rect(px, py, PORTRAIT_W, PORTRAIT_H)))
            else:
                for i, m in enumerate(members):
                    px = box_rect.x + 16 + i * 72
                    py = box_rect.y + 34
                    slots[pos].append((m, pygame.Rect(px, py, PORTRAIT_W, PORTRAIT_H)))
        return slots

    def draw_portrait_with_name(member: Character, rect: pygame.Rect):
        if getattr(member, "portrait", None):
            screen.blit(member.portrait, rect.topleft)
        else:
            pygame.draw.rect(screen, DARK_CYAN, rect)
        border_col = GREEN if member is selected_character else CYAN
        border_w = 2 if member is selected_character else 1
        pygame.draw.rect(screen, border_col, rect, border_w)
        short_name = member.name.split()[0] if member.name else ""
        name_surf = NAME_FONT.render(short_name, True, WHITE)
        screen.blit(name_surf, name_surf.get_rect(centerx=rect.centerx, top=rect.bottom + 3))

    def draw_character_info_box(character: Character | None):
        info_header = TITLE_FONT.render("CHARACTER DETAILS", True, WHITE)
        screen.blit(info_header, (INFO_BOX_RECT.x, 55))

        box_bg = pygame.Surface(INFO_BOX_RECT.size, pygame.SRCALPHA)
        box_bg.fill((10, 26, 40, 205))
        screen.blit(box_bg, INFO_BOX_RECT.topleft)
        pygame.draw.rect(screen, CYAN, INFO_BOX_RECT, 2, border_radius=6)

        pad_x = INFO_BOX_RECT.x + 14
        y = INFO_BOX_RECT.y + 14

        if character is None:
            hint1 = INFO_FONT.render("Click any character icon", True, CYAN)
            hint2 = INFO_FONT.render("to view their stats, skills,", True, CYAN)
            hint3 = INFO_FONT.render("and equipped items.", True, CYAN)
            screen.blit(hint1, (pad_x, y + 20))
            screen.blit(hint2, (pad_x, y + 44))
            screen.blit(hint3, (pad_x, y + 68))
            return

        data = get_character_inspection_data(character)

        # Header: Name & Occupation
        occ = data["occupation"].capitalize() if data["occupation"] else ""
        title_line = f"{data['name']}  ({occ})"
        screen.blit(BOX_TITLE_FONT.render(title_line, True, CYAN), (pad_x, y))
        y += 22

        # Health & Morale
        hp_line = f"HP: {data['current_health']}/{data['max_health']}    Morale: {data['morale']}"
        screen.blit(INFO_FONT.render(hp_line, True, GREEN), (pad_x, y))
        y += 20

        # Assigned Command Role & Formation Position
        role_str = data["command_role"] or "None"
        pos_str = data["position"] or "Unassigned"
        assign_line = f"Role: {role_str}  |  Pos: {pos_str}"
        screen.blit(NAME_FONT.render(assign_line, True, WHITE), (pad_x, y))
        y += 22

        pygame.draw.line(
            screen, DARK_CYAN,
            (INFO_BOX_RECT.x + 10, y),
            (INFO_BOX_RECT.right - 10, y),
            2,
        )
        y += 10

        # Two columns: Stats on left, Skills on right
        col_stats_x = pad_x
        col_skills_x = INFO_BOX_RECT.x + 215
        section_top_y = y

        screen.blit(BOX_TITLE_FONT.render("Stats", True, WHITE), (col_stats_x, section_top_y))
        stat_y = section_top_y + 22
        for _, label, val, col in data["stats"]:
            stat_surf = NAME_FONT.render(f"{label}: {val}", True, col)
            screen.blit(stat_surf, (col_stats_x, stat_y))
            stat_y += 19

        screen.blit(BOX_TITLE_FONT.render("Skills", True, WHITE), (col_skills_x, section_top_y))
        skill_y = section_top_y + 22
        if data["skills"]:
            for skill_name, val, col in data["skills"]:
                skill_surf = NAME_FONT.render(f"{skill_name}: {val}", True, col)
                screen.blit(skill_surf, (col_skills_x, skill_y))
                skill_y += 19
        else:
            screen.blit(NAME_FONT.render("None", True, (150, 170, 190)), (col_skills_x, skill_y))
            skill_y += 19

        # Equipment section below stats/skills
        equip_y = max(stat_y, skill_y) + 12
        pygame.draw.line(
            screen, DARK_CYAN,
            (INFO_BOX_RECT.x + 10, equip_y),
            (INFO_BOX_RECT.right - 10, equip_y),
            2,
        )
        equip_y += 8
        screen.blit(BOX_TITLE_FONT.render("Equipment", True, WHITE), (pad_x, equip_y))
        equip_y += 24

        if data["equipment"]:
            for item in data["equipment"]:
                if equip_y + 38 > INFO_BOX_RECT.bottom - 8:
                    break
                icon = getattr(item, "icon", None)
                if icon is not None:
                    scaled_icon = pygame.transform.scale(icon, (34, 34))
                    screen.blit(scaled_icon, (pad_x, equip_y))
                    text_x = pad_x + 42
                else:
                    text_x = pad_x
                item_name_surf = INFO_FONT.render(item.name, True, CYAN)
                screen.blit(item_name_surf, (text_x, equip_y + 2))
                desc = getattr(item, "description", "") or ""
                if desc:
                    desc_surf = NAME_FONT.render(desc[:42], True, WHITE)
                    screen.blit(desc_surf, (text_x, equip_y + 18))
                equip_y += 40
        else:
            screen.blit(NAME_FONT.render("No equipment", True, (150, 170, 190)), (pad_x, equip_y))

    clock = pygame.time.Clock()
    running = True

    while running:
        mouse_pos = pygame.mouse.get_pos()
        pool_slots = compute_pool_slots()
        command_slots = compute_command_slots()
        formation_slots = compute_formation_slots()
        ready = can_proceed(team)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False
                    break
                if PROCEED_RECT.collidepoint(event.pos):
                    if ready:
                        play_positive_click()
                        running = False
                        break
                    else:
                        play_negative_click()
                        set_status("Assign Commander, Exec Officer, and all team positions to proceed.")

                # Check if mouse clicked a character in the left pool
                clicked = False
                for member, rect in pool_slots:
                    if rect.collidepoint(event.pos):
                        selected_character = member
                        dragging_char = member
                        dragging_source = ("pool", None)
                        dragging_rect = rect.copy()
                        clicked = True
                        break

                # Check command boxes
                if not clicked:
                    for role, (member, rect) in command_slots.items():
                        if rect.collidepoint(event.pos):
                            selected_character = member
                            dragging_char = member
                            dragging_source = ("command", role)
                            dragging_rect = rect.copy()
                            clicked = True
                            break

                # Check formation boxes
                if not clicked:
                    for pos, member_list in formation_slots.items():
                        for member, rect in member_list:
                            if rect.collidepoint(event.pos):
                                selected_character = member
                                dragging_char = member
                                dragging_source = ("formation", pos)
                                dragging_rect = rect.copy()
                                clicked = True
                                break
                        if clicked:
                            break
                if clicked:
                    play_positive_click()

            elif event.type == pygame.MOUSEMOTION:
                if dragging_char and dragging_rect:
                    dragging_rect.center = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging_char and dragging_rect:
                    drop_pos = event.pos
                    handled = False

                    # 1. Check drop on Command boxes
                    for role, box_rect in COMMAND_BOX_RECTS.items():
                        if box_rect.collidepoint(drop_pos) or box_rect.colliderect(dragging_rect):
                            ok, err = assign_command_role(team, dragging_char, role)
                            if ok:
                                play_positive_click()
                            else:
                                play_negative_click()
                                if err:
                                    set_status(err)
                            handled = True
                            break

                    # 2. Check drop on Formation boxes
                    if not handled:
                        for pos, box_rect in FORMATION_BOX_RECTS.items():
                            if box_rect.collidepoint(drop_pos) or box_rect.colliderect(dragging_rect):
                                ok, err = assign_formation_position(team, dragging_char, pos)
                                if ok:
                                    play_positive_click()
                                else:
                                    play_negative_click()
                                    if err:
                                        set_status(err)
                                handled = True
                                break

                    # 3. Check drop back on Left Pool
                    if not handled and (LEFT_POOL_RECT.collidepoint(drop_pos) or LEFT_POOL_RECT.colliderect(dragging_rect)):
                        if dragging_source and dragging_source[0] == "formation":
                            unassign_formation_position(dragging_char)
                            play_positive_click()
                        elif dragging_source and dragging_source[0] == "command":
                            clear_command_role(dragging_char)
                            play_positive_click()

                    dragging_char = None
                    dragging_source = None
                    dragging_rect = None

        # ---- Draw pass ----
        screen.blit(background_image, (0, 0))

        # Top bar title & buttons
        header_surf = TITLE_FONT.render("POSITION TEAM", True, CYAN)
        screen.blit(header_surf, (25, TOP_BAR_Y + 2))

        proceed_color = CYAN if ready else (70, 100, 110)
        proceed_surf = TITLE_FONT.render("PROCEED", True, proceed_color)
        screen.blit(proceed_surf, PROCEED_RECT.topleft)
        screen.blit(EXIT_TEXT, EXIT_RECT.topleft)

        if status_timer > 0 and status_message:
            msg_surf = BOX_TITLE_FONT.render(status_message, True, RED)
            screen.blit(msg_surf, (280, TOP_BAR_Y + 4))
            status_timer -= 1

        # Left pool box
        pool_bg = pygame.Surface(LEFT_POOL_RECT.size, pygame.SRCALPHA)
        pool_bg.fill((8, 20, 32, 190))
        screen.blit(pool_bg, LEFT_POOL_RECT.topleft)
        pygame.draw.rect(screen, CYAN, LEFT_POOL_RECT, 2, border_radius=6)
        pool_title = BOX_TITLE_FONT.render("UNASSIGNED TEAM", True, CYAN)
        screen.blit(pool_title, pool_title.get_rect(centerx=LEFT_POOL_RECT.centerx, y=LEFT_POOL_RECT.y + 12))

        for member, rect in pool_slots:
            draw_portrait_with_name(member, rect)

        # Command boxes section
        cmd_header = TITLE_FONT.render("COMMAND ROLES (No Robots)", True, WHITE)
        screen.blit(cmd_header, (280, 55))

        for role, box_rect in COMMAND_BOX_RECTS.items():
            box_bg = pygame.Surface(box_rect.size, pygame.SRCALPHA)
            box_bg.fill((10, 26, 40, 190))
            screen.blit(box_bg, box_rect.topleft)
            pygame.draw.rect(screen, CYAN, box_rect, 2, border_radius=6)
            lbl = BOX_TITLE_FONT.render(ROLE_LABELS[role], True, GREEN)
            screen.blit(lbl, lbl.get_rect(centerx=box_rect.centerx, y=box_rect.y + 6))

            if role in command_slots:
                member, rect = command_slots[role]
                draw_portrait_with_name(member, rect)

        # Formation boxes section
        form_header = TITLE_FONT.render("MISSION MOVEMENT POSITIONS", True, WHITE)
        screen.blit(form_header, (280, 232))

        for pos, box_rect in FORMATION_BOX_RECTS.items():
            box_bg = pygame.Surface(box_rect.size, pygame.SRCALPHA)
            box_bg.fill((10, 26, 40, 190))
            screen.blit(box_bg, box_rect.topleft)
            pygame.draw.rect(screen, CYAN, box_rect, 2, border_radius=6)
            lbl = BOX_TITLE_FONT.render(POSITION_LABELS[pos], True, GREEN)
            screen.blit(lbl, (box_rect.x + 14, box_rect.y + 8))

            for member, rect in formation_slots[pos]:
                draw_portrait_with_name(member, rect)

        # Character inspection box on the right
        draw_character_info_box(selected_character)

        # Draw active dragged portrait on top
        if dragging_char and dragging_rect and getattr(dragging_char, "portrait", None):
            screen.blit(dragging_char.portrait, dragging_rect.topleft)
            pygame.draw.rect(screen, GREEN, dragging_rect, 2)

        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

    if stage < 1000:
        team_data = save_team_named(team_name, loop, 4, team)
    else:
        team_data = None

    pygame.quit()
    return stage + 1, team_data


async def main():
    print("Starting Stage: Position Team")
    await position_team(None)


if __name__ == "__main__":
    asyncio.run(main())

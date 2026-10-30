import asyncio

from Character import *
from DrawUtils import DrawingContext
from Item import *
from Utils import *
from MissionOrders import get_theatre_for_loop, get_mission_goals_for_theatre
from constants import TOP_BAR_Y, DEBUG


# Screen settings
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 10  # Adjust for 8 characters, reserving space for credits
MAX_TEAM_SIZE = 10
MAX_WEAPONS = 2
MAX_ARMOR = 2

async def equip_team(team_data, team_name="Debug Team", loop=1) :
    if DEBUG:
        print("started equip team")
    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Equip Your Team")

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 2)
    team = [Character.from_dict(data) for data in team_data]
    for character in team:
        character.team = team

    # Resize portraits to fit into a small area for each character
    for character in team:
        if character.portrait:
            character.portrait = pygame.transform.scale(character.portrait, (70, 80))

    # Load and play background music
    play_background_music("music/track2.mp3", pygame)

    # Load items and assign random costs and mass based on file extensions
    items_by_tab = load_item_tabs()  # Updated to return `Item` objects
    tabs = list(items_by_tab.keys())
    selected_tab = tabs[0]
    all_items = load_items_battle()

    # Credits & Mission Objective
    credits = team[0].mission.get("credits", 5000) if (team and loop > 1) else 5000
    theatre = (
        (team[0].mission.get("theatre") if team and getattr(team[0], "mission", None) else None)
        or get_theatre_for_loop(loop)
    )
    goals = get_mission_goals_for_theatre(theatre)
    mission_idx = (
        team[0].mission.get("mission_index", 0)
        if team and getattr(team[0], "mission", None)
        else 0
    ) % len(goals)
    mission_description = goals[mission_idx][0]
    stage = 3
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 18)
    MOUSEOVER_FONT = pygame.font.Font(font_path, 12)
    ITEM_DESC_FONT = pygame.font.Font(font_path, 14)
    context = DrawingContext(screen)

    PROCEED_RECT = pygame.Rect(1220, TOP_BAR_Y, 105, 25)
    PROCEED_TEXT = DEFAULT_FONT.render("PROCEED", True, CYAN)
    STORE_RECT = pygame.Rect(0, 50, ITEM_PANEL_WIDTH - 50, SCREEN_HEIGHT)
    EXIT_RECT = pygame.Rect(1400, TOP_BAR_Y, 105, 25)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)
    MESSAGE_LEFT = 300

    def display_credits():
        """Displays the current balance of credits and mission objective in the top bar."""
        #pygame.draw.rect(screen, BLACK, pygame.Rect(0, 0, SCREEN_WIDTH, CREDITS_BAR_HEIGHT))  # Background for credits bar
        credits_text = DEFAULT_FONT.render(f"Credits: {credits}", True, WHITE)
        screen.blit(credits_text, (40, 10))
        mission_text = ITEM_DESC_FONT.render(mission_description, True, CYAN)
        screen.blit(mission_text, (230, 12))

    async def display_message(text, surface, font):
        action_text_surface = font.render(text, True, CYAN)
        background_surface = pygame.Surface(
            (action_text_surface.get_width() + 150, action_text_surface.get_height() + 5))
        background_surface.fill((0, 0, 0))  # Black background
        background_position = (MESSAGE_LEFT, 5)
        surface.blit(background_surface, background_position)
        surface.blit(action_text_surface, background_position)
        pygame.display.flip()
        await asyncio.sleep(2)

    # Display item descriptions on mouseover
    def blit_item_descriptions_with_hover(surface, items, font, mouse_pos):
        for item_entry in items:
            # Check for mouse hover
            if item_entry.rect.collidepoint(mouse_pos):
                 # Render and display description if hovered
                description_surface = font.render(item_entry.description, True, WHITE)
                background_surface = pygame.Surface(
                    (description_surface.get_width() + 10, description_surface.get_height() + 10))
                background_surface.fill((125, 125, 125))  # Black background
                background_position = (item_entry.rect.left + 10, item_entry.rect.bottom + 10)
                surface.blit(background_surface, background_position)
                surface.blit(description_surface, (background_position[0] + 5, background_position[1] + 5))

    def draw_items():
        y_offset = CREDITS_BAR_HEIGHT + 40
        for item in items_by_tab[selected_tab]:
            item_icon_rect = item.icon.get_rect(topleft=(10, y_offset + 5))
            item.rect = item_icon_rect
            screen.blit(item.icon, item_icon_rect)

            # Display item properties
            property_x = item_icon_rect.right + 10
            name_text = ITEM_DESC_FONT.render(f"Name: {item.name}", True, WHITE)
            cost_text = ITEM_DESC_FONT.render(f"Cost: {item.cost} credits", True, WHITE)
            mass_text = ITEM_DESC_FONT.render(f"Mass: {item.mass} kg", True, WHITE)

            screen.blit(name_text, (property_x, y_offset))
            screen.blit(cost_text, (property_x, y_offset + 20))
            screen.blit(mass_text, (property_x, y_offset + 40))

            y_offset += 65

    def draw_dragged_item():
        """Draws only the currently dragged item or robot at its current mouse-following position."""
        if dragging_item:
            screen.blit(dragging_item.icon, dragging_item.rect)
        if dragging_robot and dragging_robot_rect:
            screen.blit(dragging_robot.portrait, dragging_robot_rect)

    def draw_team():
        """Draws character boxes and checks for encumbrance."""
        for i, character in enumerate(team):
            character_rect = pygame.Rect(ITEM_PANEL_WIDTH, CREDITS_BAR_HEIGHT + i * TEAM_BOX_HEIGHT,
                                         TEAM_PANEL_WIDTH,
                                         TEAM_BOX_HEIGHT)

            # Draw the character box with a cyan border
            pygame.draw.rect(screen, DARK_CYAN, character_rect, 2)

            # Display character portrait to the left within the equipment area
            portrait_x = character_rect.x
            portrait_y = character_rect.y
            screen.blit(character.portrait, (portrait_x, portrait_y))

            # Display character's name
            name_text = ITEM_DESC_FONT.render(character.name, True, WHITE)
            screen.blit(name_text, (character_rect.x + 10, character_rect.y + 3))

            # Draw vertical cyan separator just to the right of the portrait
            separator_x = portrait_x + 80  # Position to the right of the portrait
            pygame.draw.line(screen, DARK_CYAN, (separator_x, character_rect.y),
                             (separator_x, character_rect.y + TEAM_BOX_HEIGHT), 2)

            # Display equipped items as icons to the right of the separator line
            x_offset, y_offset = separator_x + 10, character_rect.y + 10
            for item in character.equipment:
                item.rect.topleft = (x_offset, y_offset)  # Update rect position
                screen.blit(item.icon, item.rect)
                x_offset += 60  # Space between items

            # Encumbrance warning
            if not team_has_item(team, "mulebot"):
                total_mass = character.get_carried_mass()
                if total_mass > (character.get_effective_stat_level("strength") / 2):
                    encumbered_text = DEFAULT_FONT.render("Encumbered", True, RED)
                    screen.blit(encumbered_text, (character_rect.x + 110, character_rect.y + 65))

    def display_tabs():
        """Displays tabs for item categories."""
        x_offset = 18
        for tab in TABS:
            color = GREEN if tab == selected_tab else WHITE
            tab_text = DEFAULT_FONT.render(tab.capitalize(), True, color)
            screen.blit(tab_text, (x_offset, CREDITS_BAR_HEIGHT + 10))
            x_offset += 105

    async def handle_item_drag(team, item, character):
        """
        Handles item cost deduction and adding item to character's equipment as an icon.
        Must pass basic checks:
        1. max 2 weapons per character
        2. max 2 armros per character
        3. Max team size 10 counting characters + assault bots + melee bots
        """
        if item.type == "robot":
            return await handle_robot_drag(team, item)

        if character.get_weapon_count() >= 2 and item.type == "weapon":
            play_negative_click()
            await display_message("Max two weapons per character", screen, DEFAULT_FONT)
            return
        if character.get_armor_count() >= 2 and item.type == "armor":
            play_negative_click()
            await display_message("Max two armors per character", screen, DEFAULT_FONT)
            return

        nonlocal credits
        if credits >= item.cost:
            credits -= item.cost
            if item.type != "robot":
                character.add_item(item.copy())
            play_positive_click()
        else:
            play_negative_click()
            await display_message("Not enough credits!", screen, DEFAULT_FONT)

    async def handle_robot_drag(team, item):

        if item.type == "robot" and team_size(team) >= 10:
            play_negative_click()
            await display_message("Max team size: 10", screen, DEFAULT_FONT)
            return

        nonlocal credits
        if credits >= item.cost:
            credits -= item.cost
            add_robot_to_team(team, item)
            play_positive_click()
        else:
            play_negative_click()
            await display_message("Not enough credits!", screen, DEFAULT_FONT)

    def add_robot_to_team(team, item):
        i = team_size(team)
        if item.name == "assaultbot":
          robot = Character.create_assaultbot(i, all_items)
        elif item.name == "stunbot":
          robot = Character.create_stunbot(i, all_items)
        elif item.name == "mechbot":
          robot = Character.create_mechbot(i, all_items)
        elif item.name == "techbot":
          robot = Character.create_techbot(i, all_items)
        elif item.name == "hackbot":
          robot = Character.create_hackbot(i, all_items)
        elif item.name == "meleebot":
          robot = Character.create_meleebot(i, all_items)
        elif item.name == "batonbot":
          robot = Character.create_batonbot(i, all_items)
        elif item.name == "medibot":
          robot = Character.create_medibot(i, all_items)
        elif item.name == "mulebot":
          robot = Character.create_mulebot(i, all_items)
        elif item.name == "scoutbot":
          robot = Character.create_scoutbot(i, all_items)
        else:
          return
        robot.team = team
        team.append(robot)
        # Update all members' team references so mulebot check works for everyone
        for member in team:
            member.team = team

    def handle_item_return(item):
        nonlocal credits
        credits += item.cost

    def display_character_info(character):
        """Displays the selected character's stats and skills on the left panel."""
        y_offset = CREDITS_BAR_HEIGHT + 30
        stat_title = DEFAULT_FONT.render(f"{character.name}'s Stats", True, WHITE)
        screen.blit(stat_title, (10, y_offset))
        y_offset += 30

        # Display stats
        for stat, value in character.stats.items():
            color = color_for_stat(value)
            if stat == "max_health" or stat == "meleecombat" or stat == "surprise":
                color = color_for_stat(round(value / 2))
            if stat == "movement" or stat == "leadership":
                color = color_for_stat(round(value / 3))
            stat_text = ITEM_DESC_FONT.render(f"{stat.capitalize()}: {value}", True, color)
            screen.blit(stat_text, (10, y_offset))
            y_offset += 20

        y_offset += 20  # Add space between stats and skills

        # Display skills
        skill_title = DEFAULT_FONT.render("Skills:", True, WHITE)
        screen.blit(skill_title, (10, y_offset))
        y_offset += 30
        for skill, proficiency in character.skills.items():
            color = color_for_skill(proficiency)
            skill_text = ITEM_DESC_FONT.render(f"{skill}: {proficiency}", True, color)
            screen.blit(skill_text, (10, y_offset))
            y_offset += 20

    # Variables to track dragging state
    dragging_item = None
    original_dragging_item = None
    original_item_position = None
    dragging_from_character = None
    dragging_robot = None
    dragging_robot_rect = None

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage2.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    # Variables to track character information display vs item store display
    selected_character = None  # Track which character is selected, if any
    showing_character_info = False  # Toggle to switch between items and character info view

    # Main Game Loop
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if PROCEED_RECT.collidepoint(event.pos):
                    play_positive_click()
                    running = False
                elif EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False

                # Check for tab selection if not viewing character info
                if not showing_character_info:
                     for tab in tabs:
                        tab_text_rect = pygame.Rect(10 + tabs.index(tab) * 110, CREDITS_BAR_HEIGHT + 10, 110, 30)
                        if tab_text_rect.collidepoint(mouse_pos):
                             play_positive_click()
                             selected_tab = tab

                # Check if clicking on a character to toggle their info display
                # Clicking on a robot instead starts a drag to return it to the store
                character_clicked = False
                for i, character in enumerate(team):
                    character_rect = pygame.Rect(ITEM_PANEL_WIDTH, CREDITS_BAR_HEIGHT + i * TEAM_BOX_HEIGHT,
                                                 80, TEAM_BOX_HEIGHT)
                    if character_rect.collidepoint(mouse_pos):
                        if character.type == "robot":
                            # Begin dragging the robot back toward the store
                            dragging_robot = character
                            dragging_robot_rect = pygame.Rect(
                                ITEM_PANEL_WIDTH, CREDITS_BAR_HEIGHT + i * TEAM_BOX_HEIGHT, 70, 80)
                        else:
                            play_positive_click()
                            if selected_character == character:
                                # If the same character is clicked again, toggle off
                                showing_character_info = not showing_character_info
                            else:
                                # Select new character and show info
                                selected_character = character
                                showing_character_info = True
                        character_clicked = True
                        break

                # If not clicking on a character, reset the view to items
                if not character_clicked:
                    selected_character = None
                    showing_character_info = False

                # Check if clicking on an item in the left panel (for new purchases)
                for item in items_by_tab[selected_tab]:
                    if item.rect.collidepoint(mouse_pos):
                        dragging_item = item.copy()
                        dragging_item.rect = pygame.Rect(mouse_pos[0], mouse_pos[1], 50, 50)
                        original_item_position = dragging_item.rect.topleft
                        dragging_from_character = None  # Not from a character's inventory

                # Check if clicking on an item in a character's equipment
                for character in team:
                    if character.type != "robot":
                        for item in character.equipment:
                            item_rect = pygame.Rect(item.icon.get_rect(topleft=(item.rect.topleft)))
                            if item_rect.collidepoint(mouse_pos):
                                original_dragging_item = item
                                dragging_item = item.copy()
                                dragging_item.rect = item.rect.copy()
                                dragging_from_character = character
                                original_item_position = item_rect.topleft
                                break

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging_item:
                    dropped_on_character = None

                    # Check if dropped on a different character
                    for i, character in enumerate(team):
                        character_rect = pygame.Rect(ITEM_PANEL_WIDTH, CREDITS_BAR_HEIGHT + i * TEAM_BOX_HEIGHT,
                                                     TEAM_PANEL_WIDTH, TEAM_BOX_HEIGHT)
                        if character_rect.colliderect(dragging_item.rect) and character.type != "robot":
                            dropped_on_character = character
                            break

                    print(f"dropped_on_character: {dropped_on_character}, dragging_from_character: {dragging_from_character}")

                    if dropped_on_character:
                        # If dropped on a different character, move the item
                        if dragging_from_character and dragging_from_character != dropped_on_character:
                            if dropped_on_character.get_weapon_count() >= 2 and dragging_item.type == "weapon":
                                play_negative_click()
                                await display_message("Max two weapons per character", screen, DEFAULT_FONT)
                                dragging_item.rect.topleft = original_item_position
                            elif dropped_on_character.get_armor_count() >= 2 and dragging_item.type == "armor":
                                play_negative_click()
                                await display_message("Max two armors per character", screen, DEFAULT_FONT)
                                dragging_item.rect.topleft = original_item_position
                            else:
                                play_positive_click()
                                dragging_from_character.equipment.remove(original_dragging_item)
                                dropped_on_character.equipment.append(dragging_item)
                        elif dragging_from_character:
                            dragging_item.rect.topleft = original_item_position
                        else:
                            # handle as a new purchase with various checks
                            await handle_item_drag(team, dragging_item, dropped_on_character)
                    elif STORE_RECT.collidepoint(dragging_item.rect.center):
                        if dragging_from_character:
                            play_positive_click()
                            dragging_from_character.equipment.remove(original_dragging_item)
                            handle_item_return(original_dragging_item)
                    else:
                        # If it's a robot dropped in open space, add it to the team
                        if dragging_item.type == "robot" and not dragging_from_character:
                            await handle_item_drag(team, dragging_item, None)
                        else:
                            # Return to the original position if not equipped
                            dragging_item.rect.topleft = original_item_position

                    dragging_item = None
                    original_dragging_item = None
                    dragging_from_character = None
                    original_item_position = None

                if dragging_robot and dragging_robot_rect:
                    if STORE_RECT.collidepoint(dragging_robot_rect.center):
                        play_positive_click()
                        # Refund only the robot's purchase cost; its equipment stays
                        refund = all_items[dragging_robot.occupation].cost
                        credits += refund
                        await display_message(f"Sold {dragging_robot.name} for {refund} credits", screen, DEFAULT_FONT)
                        team.remove(dragging_robot)
                    dragging_robot = None
                    dragging_robot_rect = None

            elif event.type == pygame.MOUSEMOTION:
                # Dragging an item
                if dragging_item:
                    dragging_item.rect.center = mouse_pos  # Move the item to follow the mouse pointer
                if dragging_robot and dragging_robot_rect:
                    dragging_robot_rect.center = mouse_pos

        # Draw background first
        screen.blit(background_image, (0, 0))

        # Draw UI Elements
        display_credits()

        # Conditionally display either items or the selected character's info
        if showing_character_info and selected_character:
            display_character_info(selected_character)
        else:
            display_tabs()
            draw_items()
        draw_team()
        draw_dragged_item()
        screen.blit(PROCEED_TEXT, PROCEED_RECT)
        screen.blit(EXIT_TEXT, EXIT_RECT)

        # blit item descriptions on hover
        blit_item_descriptions_with_hover(screen, items_by_tab[selected_tab], ITEM_DESC_FONT, mouse_pos)

        pygame.display.flip()
        await asyncio.sleep(0)

    # modifications for traitors, psychos, and unvetted characters
    for member in team:
        if member.type == "robot":
            continue

        # Unvetted: 10% chance they misrepresented their skills
        # Lower 1-3 randomly chosen skills by 10-25%
        if not member.vetted and random.randint(1, 100) <= 10:
            skill_names = list(member.skills.keys())
            if skill_names:
                n = random.randint(1, min(3, len(skill_names)))
                for skill in random.sample(skill_names, n):
                    reduction = random.uniform(0.10, 0.25)
                    member.skills[skill] = max(1, int(member.skills[skill] * (1 - reduction)))

        # Traitors: covert training grants or boosts Espionage and/or Hacking
        # 75% chance of Espionage skill (or +20 if they already have it)
        # 50% chance of Hacking skill (or +20 if they already have it)
        if member.traitor:
            if random.randint(1, 100) <= 75:
                current = member.skills.get("Espionage", 0)
                member.skills["Espionage"] = min(100, max(current + 20, 40))
            if random.randint(1, 100) <= 50:
                current = member.skills.get("Hacking", 0)
                member.skills["Hacking"] = min(100, max(current + 20, 40))

    # save characters upon exit
    add_team_mission_param(team, "credits", credits)
    if stage < 1000:
        team_data = save_team_named(team_name, loop, 3, team)
    else:
        team_data = None

    pygame.quit()

    return stage + 1, team_data

async def main():
    print("Starting Stage: Equip Team")
    team_data = equip_team(None)

if __name__ == "__main__":
    main()
import pygame
import sys

from Utils import *

# ---------------------------------------------------------------------------
# Colours / fonts
# ---------------------------------------------------------------------------
BG_COLOR      = (10, 15, 25)
BORDER_COLOR  = (0, 180, 200)
HIGHLIGHT     = (0, 255, 255)
DIM           = (100, 140, 160)
TEXT_COLOR    = (255, 255, 255)
BUTTON_COLOR  = (0, 60, 80)
BUTTON_HOVER  = (0, 100, 130)

STAGE_LABELS = {
    1: "Choose Team",
    2: "Mission Orders",
    3: "Equip Team",
    4: "Voyage",
    5: "Mission",
    6: "Return Voyage",
}

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
MARGIN        = 60          # left edge of content
CONT_W        = 380         # Continue button width
CONT_H        = 38
DEV_W         = 130         # [Dev] Stages button width
DEV_H         = 38
DEL_W         = 100         # Delete button width
DEL_H         = 38
TEAM_ROW_H    = 28          # height of the team name label row
BUTTON_ROW_H  = 44          # height of the button row (cont + dev + del)
STAGE_ROW_H   = 32          # height of each expanded stage entry
SECTION_GAP   = 14          # gap between team blocks

DEL_COLOR     = (80, 20, 20)    # normal delete button
DEL_CONFIRM   = (160, 80, 0)    # pending-confirmation state (amber)
DEL_HOVER_N   = (120, 30, 30)   # hover on normal
DEL_HOVER_C   = (200, 110, 0)   # hover on confirm

# ---------------------------------------------------------------------------
def load_game():
    """
    Show the Load Game startup screen.
    Returns (team_name, loop, start_stage, team_data).
      team_name  : display name (spaces preserved)
      loop       : loop to resume
      start_stage: next stage to run (saved_stage + 1)
      team_data  : list of character dicts, or [] for New Game
    Returns ("__new__", 1, 0, []) for New Game.
    """
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Explorers — Load Game")

    font_path  = resource_path("fonts/Orbitron-Bold.ttf")
    title_font = pygame.font.Font(font_path, 28)
    team_font  = pygame.font.Font(font_path, 20)
    cont_font  = pygame.font.Font(font_path, 14)
    dev_font   = pygame.font.Font(font_path, 11)

    def display_name(folder):
        return folder.replace("_", " ")

    teams      = list_teams()
    team_saves = {display_name(t): latest_saves_for_team(display_name(t)) for t in teams}
    expanded   = {display_name(t): False for t in teams}
    confirm_del = {}   # tname -> True when awaiting second-click confirmation

    # New Game button — centred near the top
    ng_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 60, 240, 46)

    clock  = pygame.time.Clock()
    result = None

    while result is None:
        mouse = pygame.mouse.get_pos()

        # ---- Events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and ng_rect.collidepoint(event.pos)):
                result = ("__new__", 1, 0, [])
                break

            # Walk team rows — rebuild positions same as draw pass
            y = 148
            clicked_del = False
            for tname, saves in list(team_saves.items()):
                y += TEAM_ROW_H           # name label
                # Continue button row
                del_rect = pygame.Rect(
                    MARGIN + CONT_W + 12 + DEV_W + 10, y, DEL_W, DEL_H)
                if saves:
                    latest_stage = max(saves.keys())
                    lp = saves[latest_stage]
                    cont_rect = pygame.Rect(MARGIN, y, CONT_W, CONT_H)
                    dev_rect  = pygame.Rect(MARGIN + CONT_W + 12, y, DEV_W, DEV_H)

                    if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                        if cont_rect.collidepoint(event.pos):
                            td = load_team_named(tname, lp, latest_stage)
                            result = (tname, lp, latest_stage + 1, td)
                            break
                        if dev_rect.collidepoint(event.pos):
                            expanded[tname] = not expanded[tname]
                            confirm_del.pop(tname, None)
                            clicked_del = True

                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                        and del_rect.collidepoint(event.pos)):
                    clicked_del = True
                    if confirm_del.get(tname):
                        # Second click — delete and refresh
                        delete_team(tname)
                        del team_saves[tname]
                        expanded.pop(tname, None)
                        confirm_del.pop(tname, None)
                    else:
                        # First click — enter confirmation state
                        confirm_del = {tname: True}  # reset others

                y += BUTTON_ROW_H

                # Expanded stage list
                if expanded.get(tname) and saves:
                    for st in sorted(saves.keys()):
                        lp2 = saves[st]
                        st_rect = pygame.Rect(MARGIN + 20, y, CONT_W + DEV_W, STAGE_ROW_H)
                        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                                and st_rect.collidepoint(event.pos)):
                            td = load_team_named(tname, lp2, st)
                            result = (tname, lp2, st + 1, td)
                            break
                        y += STAGE_ROW_H
                    if result:
                        break

                y += SECTION_GAP  # separator gap

            # Any click that didn't land on a delete button resets confirmation
            if (event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1 and not clicked_del):
                confirm_del.clear()

            if result:
                break

        # ---- Draw ----
        screen.fill(BG_COLOR)

        # Title
        title = title_font.render("EXPLORERS  —  SELECT TEAM", True, HIGHLIGHT)
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=14))

        # New Game button
        ng_col = BUTTON_HOVER if ng_rect.collidepoint(mouse) else BUTTON_COLOR
        pygame.draw.rect(screen, ng_col, ng_rect, border_radius=7)
        pygame.draw.rect(screen, BORDER_COLOR, ng_rect, 2, border_radius=7)
        ng_lbl = team_font.render("NEW GAME", True, TEXT_COLOR)
        screen.blit(ng_lbl, ng_lbl.get_rect(center=ng_rect.center))

        # Divider
        pygame.draw.line(screen, BORDER_COLOR, (40, 138), (SCREEN_WIDTH - 40, 138), 1)

        if not team_saves:
            msg = dev_font.render("No saved teams found.", True, DIM)
            screen.blit(msg, (MARGIN, 155))
        else:
            y = 148
            for tname, saves in team_saves.items():
                # ---- Team name label ----
                name_surf = team_font.render(tname, True, HIGHLIGHT)
                screen.blit(name_surf, (MARGIN, y))
                y += TEAM_ROW_H

                if saves:
                    latest_stage = max(saves.keys())
                    lp = saves[latest_stage]
                    stage_label = STAGE_LABELS.get(latest_stage, f"Stage {latest_stage}")

                    # Continue button
                    cont_rect = pygame.Rect(MARGIN, y, CONT_W, CONT_H)
                    cont_col  = BUTTON_HOVER if cont_rect.collidepoint(mouse) else BUTTON_COLOR
                    pygame.draw.rect(screen, cont_col, cont_rect, border_radius=6)
                    pygame.draw.rect(screen, BORDER_COLOR, cont_rect, 2, border_radius=6)
                    cont_lbl = cont_font.render(
                        f"CONTINUE  -  {stage_label}  (Loop {lp})", True, HIGHLIGHT)
                    screen.blit(cont_lbl, cont_lbl.get_rect(
                        midleft=(cont_rect.x + 14, cont_rect.centery)))

                    # [Dev] expand/collapse
                    dev_rect = pygame.Rect(MARGIN + CONT_W + 12, y, DEV_W, DEV_H)
                    dev_col  = BUTTON_HOVER if dev_rect.collidepoint(mouse) else (25, 35, 55)
                    pygame.draw.rect(screen, dev_col, dev_rect, border_radius=6)
                    pygame.draw.rect(screen, DIM, dev_rect, 1, border_radius=6)
                    dev_lbl = dev_font.render(
                        "[Dev] Hide" if expanded[tname] else "[Dev] Stages", True, DIM)
                    screen.blit(dev_lbl, dev_lbl.get_rect(center=dev_rect.center))

                    # Delete button
                    del_rect = pygame.Rect(
                        MARGIN + CONT_W + 12 + DEV_W + 10, y, DEL_W, DEL_H)
                    pending = confirm_del.get(tname, False)
                    if pending:
                        del_bg = DEL_HOVER_C if del_rect.collidepoint(mouse) else DEL_CONFIRM
                        del_text = "CONFIRM?"
                        del_border = (255, 160, 0)
                    else:
                        del_bg = DEL_HOVER_N if del_rect.collidepoint(mouse) else DEL_COLOR
                        del_text = "DELETE"
                        del_border = (180, 40, 40)
                    pygame.draw.rect(screen, del_bg, del_rect, border_radius=6)
                    pygame.draw.rect(screen, del_border, del_rect, 2, border_radius=6)
                    del_lbl = dev_font.render(del_text, True, (255, 200, 200))
                    screen.blit(del_lbl, del_lbl.get_rect(center=del_rect.center))

                    y += BUTTON_ROW_H

                    # Expanded stage entries
                    if expanded.get(tname):
                        for st in sorted(saves.keys()):
                            lp2 = saves[st]
                            stage_label2 = STAGE_LABELS.get(st, f"Stage {st}")
                            st_rect = pygame.Rect(MARGIN + 20, y, CONT_W + DEV_W, STAGE_ROW_H)
                            st_col  = BUTTON_HOVER if st_rect.collidepoint(mouse) else (20, 32, 50)
                            pygame.draw.rect(screen, st_col, st_rect, border_radius=4)
                            pygame.draw.rect(screen, DIM, st_rect, 1, border_radius=4)
                            st_lbl = dev_font.render(
                                f"{stage_label2}  -  Loop {lp2}", True, TEXT_COLOR)
                            screen.blit(st_lbl, st_lbl.get_rect(
                                midleft=(st_rect.x + 12, st_rect.centery)))
                            y += STAGE_ROW_H
                else:
                    no_save = dev_font.render("no saves", True, DIM)
                    screen.blit(no_save, (MARGIN + CONT_W + 20, y + 10))
                    y += BUTTON_ROW_H

                # Separator line
                pygame.draw.line(screen, (28, 42, 62),
                                 (40, y + 4), (SCREEN_WIDTH - 40, y + 4), 1)
                y += SECTION_GAP

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return result

import pygame
import sys
import asyncio

from LoadGame import load_game
from Intro import introduction3
from ChooseTeam4 import choose_team
from MissionOrders import mission_orders
from EquipTeam2 import equip_team
from PositionTeam import position_team
from Voyage import voyage
from Mission import go_mission
from ReturnVoyage import return_voyage
from Score import score


async def main(stage, mission):

    # Show load/save screen first
    team_name, loop, start_stage, team_data = await load_game()

    if team_name == "__new__":
        # Fresh game — run intro then start from stage 1
        team_data = []
        team_name = "unnamed"
        loop = 1
        print("Starting Stage: Introduction")
        stage = await introduction3()
        print(stage)
        await run_mission(stage, loop, team_name, team_data)
    else:
        # Resume from the chosen stage
        print(f"Resuming team '{team_name}' at stage {start_stage}, loop {loop}")
        await run_mission(start_stage, loop, team_name, team_data)


async def run_mission(stage, loop, team_name, team_data):
    # Stage 1: Form Team / Replace Members
    if stage == 1:
        print("Starting Stage: Choose Team")
        stage, team_data, team_name = await choose_team(team_data, team_name, loop)

    # Stage 2: Mission Orders
    if stage == 2:
        print("Starting Stage: Mission Orders")
        stage, team_data = await mission_orders(team_data, team_name, loop)

    # Stage 3: Equip Team
    if stage == 3:
        print("Starting Stage: Equip Team")
        stage, team_data = await equip_team(team_data, team_name, loop)

    # Stage 4: Position Team
    if stage == 4:
        print("Starting Stage: Position Team")
        stage, team_data = await position_team(team_data, team_name, loop)

    # Stage 5: Voyage
    if stage == 5:
        print("Starting Stage: Voyage")
        stage, team_data = await voyage(team_data, team_name, loop)

    # Stage 6: Mission
    if stage == 6:
        print("Starting Stage: Mission")
        stage, team_data = await go_mission(team_data, team_name, loop)

    # Team died or player quit during mission — restart from load screen
    if stage >= 1000:
        print("Restarting from load screen (team death or quit).")
        await main(0, 0)
        return

    # Stage 7: Return Voyage
    if stage == 7:
        print("Starting Stage: Return Voyage")
        stage, team_data = await return_voyage(team_data, team_name, loop)

    # Team died during return voyage — restart from load screen
    if stage >= 1000:
        print("Restarting from load screen (team death or quit).")
        await main(0, 0)
        return

    # Stage 8: Score
    if stage == 8:
        print("Starting Stage: Score")
        stage, team_data = await score(team_data, team_name, loop)

        # PROCEED — re-enter the loop at stage 1 with incremented loop number
        if stage == 1:
            new_loop = loop + 1
            print(f"Proceeding to loop {new_loop}")
            await run_mission(1, new_loop, team_name, team_data)
        # EXIT (stage == 1000) — team already saved inside score(); just fall through

if __name__ == "__main__":
    asyncio.run(main(0, 0))
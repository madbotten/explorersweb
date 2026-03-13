import pygame
import sys

from Intro import introduction3
from ChooseTeam4 import choose_team
from MissionOrders import mission_orders
from EquipTeam2 import equip_team
from Voyage import voyage
from Mission import mission
from ReturnVoyage import return_voyage
from Score import score


def main(stage, mission):

    # Stage 0: Intro
    team_data = []
    print("Starting Stage: Introduction")
    stage = introduction3()
    print(stage)

    if stage <= 7:
        run_mission(stage, mission, team_data)
    else:
        run_mission(stage, mission + 1, team_data)

def run_mission(stage, mission, team_data):
    # Stage 1: Form Team / Replace Members
    if stage == 1:
        print("Starting Stage: Choose Team")
        stage, team_data = choose_team(team_data)

    # Stage 2: Mission Orders
    if stage == 2:
        print("Starting Stage: Mission Orders")
        stage, team_data = mission_orders(team_data)

    # Stage 3: Equip Team
    if stage == 3:
        print("Starting Stage: Equip Team")
        stage, team_data = equip_team(team_data)

    # Stage 4: Voyage
    if stage == 4:
        print("Starting Stage: Voyage")
        stage, team_data = voyage(team_data)

    # Stage 5: Mission
    if stage == 5:
        print("Starting Stage: Mission")
        stage, team_data = mission(team_data)

    # Stage 6: Return Voyage
    if stage == 6:
        print("Starting Stage: Return Voyage")
        stage, team_data = return_voyage(team_data)

    # Stage 6: Score
    if stage == 7:
        print("Starting Stage: Score")
        score(team_data)

if __name__ == "__main__":
    main(0, 0)
from riotwatcher import LolWatcher, ApiError
import queue
import numpy as np
import csv
import json
import statistics

def get_players_from_match(match_info, player_list):
    new_players = []
    for player in match_info["participantIdentities"]:
        account_id = player["player"]["accountId"]
        if account_id not in player_list:
            new_players.append(account_id)
            player_list.append(account_id)

    return new_players

def get_matches_from_player_list(lolwatcher, new_players, visited_matches):
    total_match_set = set()
    for playerId in new_players:
         match_list = lolwatcher.match.matchlist_by_account("na1", playerId)
         for game in match_list["matches"]:
             if game["queue"] == 440 or game["queue"] == 420:
                 match_id = game["gameId"]
                 if match_id not in visited_matches:
                     total_match_set.add(match_id)
    return list(total_match_set)

# data collection
def data_collection(start_match_id, api_key, minute=15):
    # write_to_csv_header(minute)
    my_region = 'na1'
    w = LolWatcher(api_key,1)
    visited_match = []
    match_queue = queue.Queue()
    visited_player_list = []
    match_queue.put(start_match_id)
    match_data = []
    # while not match_queue.empty():
    # for i in range(5):
    counter = 0
    while True:
        print("currently match ", counter)
        try:
            match_id = match_queue.get()
            if match_id in visited_match:
                print("match already visited", match_id)
                continue
            visited_match.append(match_id)
            # all the match information
            match_timeline = w.match.timeline_by_match(my_region, match_id)["frames"]
            match_basic_info = w.match.by_id(my_region, match_id)
            write_to_json(match_timeline, "match_timeline")
            write_to_json(match_basic_info, "match_basic_info")
            # parse match
            data_row = parse_match(match_timeline, match_basic_info, w, minute)
            match_data.append(data_row)
            write_to_csv_one_row(data_row, minute)
            # add new matches to match queue
            counter += 1
            if match_queue.qsize() > 1000:
                print("queue size greater than 1000 --- > pass")
                continue
            new_players = get_players_from_match(match_basic_info, visited_player_list)
            new_matches = get_matches_from_player_list(w, new_players, visited_match)
            # add matches to queue
            for new_match_id in new_matches:
                match_queue.put(new_match_id)
        except Exception as e:
            print("encounter error continue \n", e)
            continue

    # write_to_csv(match_data, minute)
    return match_data

def write_to_csv_header(minute):
    filename = "match_data_at_"+str(minute) +" minute.csv"
    fields = [
        "current_gold", "total_gold", "level", "xp", "cs", "jg", "champion_mastery", "damage_taken_per_min",
        "champion_mastery_median", "champion_mastery_min"
        , "ward_placed", "elite_monster_killed", "building_killed", "champion_killed", "winner"]

    # writing to csv file
    with open(filename, 'w') as csvfile:
        # creating a csv writer object
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)

def write_to_csv_one_row(one_row_data, minute):
    if one_row_data==None:
        return
    filename = "match_data_at_"+str(minute) +" minute.csv"
    # writing to csv file
    with open(filename, 'a') as csvfile:
        # creating a csv writer object
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(one_row_data)

def write_to_csv(match_data, minute):
    filename = "final_match_data_at_"+str(minute) +" minute.csv"
    fields = [
    "current_gold", "total_gold", "level", "xp", "cs", "jg", "champion_mastery", "damage_taken_per_min", "champion_mastery_median", "champion_mastery_min"
        , "ward_placed", "elite_monster_killed",  "building_killed", "champion_killed", "winner"]

    # writing to csv file
    with open(filename, 'w') as csvfile:
        # creating a csv writer object
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(match_data)

def write_to_json(match_dict, timeline_or_basic):
    filePath = timeline_or_basic + ".json"
    with open(filePath, "a") as outfile:
        string_output = json.dumps(match_dict) + "\n"
        outfile.write(string_output)


def load_json_to_dict(filename):
    basic_mactch_info = []
    for line in open('match_basic_info.json', 'r'):
        basic_mactch_info.append(json.loads(line))
    return

def parse_match(match_timeline, match_basic_info, w, minute):
    my_region = "na1"
    game_duration = len(match_timeline)
    # if game too short
    if game_duration < 25:
        return None
    difference_data_row = []
    team1_data = np.zeros(6)
    team2_data = np.zeros(6)
    winner = ""
    if match_basic_info["teams"][0]["win"] == "Win":
        winner = 0
    else:
        winner = 1
    # iterate through timeline at 10 miniutes for all players
    event = match_timeline[minute]["events"]
    players_frame = match_timeline[minute]["participantFrames"]
    for key, player in players_frame.items():
        player_id = player["participantId"]
        current_gold = player["currentGold"]
        total_gold = player["totalGold"]
        level = player["level"]
        xp = player["xp"]
        cs = player["minionsKilled"]
        jg = player["jungleMinionsKilled"]
        current_play_data = np.array([current_gold, total_gold, level, xp, cs, jg])
        if player_id in range(1,6):
            team1_data += current_play_data
        else:
            team2_data += current_play_data

    difference_data_row = (team1_data - team2_data).tolist()

    # parse basic match info
    team1_data1 = np.zeros(2)
    team2_data1 = np.zeros(2)
    players_info = match_basic_info["participantIdentities"]
    team1_mastery = []
    team2_mastery = []
    for player in match_basic_info["participants"]:
        player_id = player["participantId"]
        champion_id = player["championId"]
        summorner_id = players_info[player_id-1]["player"]["summonerId"]
        champion_mastery =  w.champion_mastery.by_summoner_by_champion(my_region, summorner_id, champion_id)["championPoints"]
        # champion_mastery = 0
        damage_taken_per_min = player["timeline"]["damageTakenPerMinDeltas"]["0-10"]
        # damage_taken_per_min = player["timeline"]["damageTakenPerMinDeltas"]["10-20"]

        current_play_data = np.array([champion_mastery, damage_taken_per_min])
        if player_id in range(1,6):
            team1_mastery.append(champion_mastery)
            team1_data1 += current_play_data
        else:
            team2_mastery.append(champion_mastery)
            team2_data1 += current_play_data
    median_mastery_diff = statistics.median(team1_mastery) - statistics.median(team2_mastery)
    min_mastery_diff = min(team1_mastery) - min(team2_mastery)

    difference_data_row1 = (team1_data1 - team2_data1).tolist()
    difference_data_row1.append(median_mastery_diff)
    difference_data_row1.append(min_mastery_diff)

    # parse event from 0 - 10 minutes
    # ward placed, elite monster killed,
    team1_data2 = [0,0,0,0]
    team2_data2 = [0,0,0,0]
    for frame_num in range(minute):
        events = match_timeline[frame_num]["events"]
        for event in events:
            if event["type"] == "WARD_PLACED":
                player_id = event["creatorId"]
                if player_id in range(1, 6):
                    team1_data2[0] += 1
                else:
                    team2_data2[0] += 1

            elif event["type"] == "ELITE_MONSTER_KILL":
                player_id = event["killerId"]
                if player_id in range(1, 6):
                    team1_data2[1] += 1
                else:
                    team2_data2[1] += 1

            elif event["type"] == "BUILDING_KILL":
                player_id = event["killerId"]
                if player_id in range(1, 6):
                    team1_data2[2] += 1
                else:
                    team2_data2[2] += 1
            elif event["type"] == "CHAMPION_KILL":
                player_id = event["killerId"]
                if player_id in range(1, 6):
                    team1_data2[3] += 1
                else:
                    team2_data2[3] += 1
    difference_data_row2 =(np.array(team1_data2) - np.array(team2_data2)).tolist()





    # current_gold, total_gold, level, xp, cs, jg, champion_mastery, damage_taken_per_min, champion_mastery_median,  champion_mastery_min, ward placed, elite monster_killed, BUILDING_KILL, champion_kill, winner
    final = difference_data_row + difference_data_row1 + difference_data_row2
    final.append(winner)
    return final








def match_files_to_csv(api_key, minute):
    w = LolWatcher(api_key,1)
    write_to_csv_header(minute)
    basic_mactch_info = []
    match_data = []
    for line in open('match_basic_info.json', 'r'):
        basic_mactch_info.append(json.loads(line))
    counter = 0
    for line in open('match_timeline.json', 'r'):
        print("current match ", counter)
        match_timeline = json.loads(line)
        match_basic_info = basic_mactch_info[counter]
        counter += 1
        data_row = parse_match(match_timeline, match_basic_info, w, minute)
        write_to_csv_one_row(data_row, minute)
        print(data_row)
        if data_row==None:
            continue
        match_data.append(data_row)
    write_to_csv(match_data, minute)
    return match_data

# match_files_to_csv("RGAPI-f17efd07-2431-4841-acb4-4a70ecafe7bd", 15)
# minute = 15
# api_key = 'RGAPI-af895a1c-494d-4563-8971-f513a2e963ca'

# # my_region = 'na1'
# # w = LolWatcher(api_key)
# # name = "Xiao Kë Ai"
# # id = w.summoner.by_name(summoner_name=name, region=my_region)["id"]
# # account_id = w.summoner.by_name(summoner_name=name, region=my_region)["accountId"]
# # match_list = w.match.matchlist_by_account(my_region, account_id)
#
# game_id = 3869814594
# data_collected = data_collection(game_id, api_key, minute)

# match_basic_info = w.match.by_id(my_region, 3880482149)
# print(match_basic_info)
# match_timeline = w.match.timeline_by_match(my_region, 3880482149)["frames"]
# match_at_minute = match_timeline[minute]
# id = w.summoner.by_name(summoner_name="C9 Sneaky", region=my_region)["id"]
# account_id = w.summoner.by_name(summoner_name="C9 Sneaky", region=my_region)["accountId"]
#
# mastery = w.champion_mastery.by_summoner_by_champion(my_region, id, 110)
# match_list = w.match.matchlist_by_account(my_region, account_id)
# parsed = parse_match(match_timeline, match_basic_info, w)

# write_to_csv(data_collected)
#
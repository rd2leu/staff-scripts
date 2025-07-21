import requests, json, time, os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import rank2mmr
from utilities import datestr, read_google_sheet
from utilities2 import extract_account_id, extract_account_ids

from sklearn.cluster import DBSCAN as DBS

INPUT_PATH = 'input'
OUTPUT_PATH = 'draft'
FNAME = 'rd2l_s31'

"""
Sheet styles:
0 unspecified, assume Owl sheets
1 Owl sheets: < S27: no hyperlinks, alts in a single cell
2 Moggoblin sheets: M14 S28: no hyperlinks, alts in "2nd account" "3rd account"
3 Moggoblin sheets: M15 S29: dotabuff urls hyperlinked, alts in "2nd account" "3rd account"
4 BYOB Shakira Cup 2024
"""

with open(os.path.join(INPUT_PATH, FNAME + '.json'), 'r') as f:
    rd2l = json.load(f)

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:

            dsparser = 0
            if 'dsparser' in division:
                dsparser = division['dsparser']
            if dsparser > 4:
                raise NotImplementedError('no parser for draft sheet style')
                # crash here

            ## parse draft sheet
            if dsparser in [0, 1, 2]:
                draft = read_google_sheet(division['draftsheet'])
            elif dsparser in [3, 4]:
                # hyperlinked cells for account url
                draft = read_google_sheet(division['draftsheet'], resolve_links = True)
            draft = draft[draft['Activity check'] == 'Yes']

            if dsparser in [0, 1]:
                # Owl sheets
                draft['account_id'] = draft['Dotabuff link'].apply(extract_account_id)
                alts = draft['Please list your alternate accounts'].fillna('')
                draft['alts'] = alts.apply(extract_account_ids)
            elif dsparser in [2, 3]:
                # Moggoblin sheets
                link_col_options = ['dotabuff link', 'stratz link', 'account link']
                link_col = next(c for c in draft.columns if c.lower() in link_col_options)
                draft['account_id'] = draft[link_col].apply(extract_account_id)
                alts = draft[['Second account', 'Third account']].fillna('').apply(' '.join, axis = 1)
                draft['alts'] = alts.apply(extract_account_ids)
                draft = draft[draft['Activity check'].isin(['Yes', 'yes'])].copy()
            elif dsparser in [4]:
                # BYOB
                draft['account_id'] = draft['Account Link'].apply(extract_account_id)
                draft['alts'] = draft.apply(lambda x: [], axis = 1)

            draft['accounts'] = draft.apply(lambda x: x['alts'] + [x['account_id']], axis = 1)

            pos_idx = draft.columns.searchsorted('Pos 1') + 1
            
            ## search teamsheet for teams
            players = {}

            # BYOB
            if league['type'] == 'byob':
                #draft.groupby('Group Contact')['Name'].agg(list)
                # you can't trust people to write the same name
                # so for now, group by index
                teams2 = []
                draft['country'] = draft['account_id'].apply(lambda a: get_player_data(a)['country'])
                for i in range(0, len(draft), 5):
                    team = {}
                    # captain
                    team['name'] = draft.iloc[i: i + 5]['Name'].to_list()
                    team['account_id'] = draft.iloc[i: i + 5]['account_id'].to_list()
                    team['mmr'] = draft.iloc[i: i + 5]['MMR Peak'].to_list()
                    team['discord'] = draft.iloc[i: i + 5]['Discord ID'].to_list()
                    team['pos_pref'] = draft.iloc[i: i + 5, pos_idx - 1: pos_idx + 4].values.astype(int).tolist()
                    team['alts'] = draft.iloc[i: i + 5]['alts'].to_list()
                    team['country'] = draft.iloc[i: i + 5]['country'].to_list()
                    teams2 += [
                        {'name': draft.iloc[i: i + 5]['Group Contact'].values[0],
                         'players': [{k: v[j] for k, v in team.items()} for j in range(5)]
                         }]
       
            else:

                # read team sheet
                sheet = read_google_sheet(division['teamsheet'])
                sheet.fillna('', inplace = True)

                tsparser = 0
                if 'tsparser' in division:
                    tsparser = division['tsparser']
                if tsparser > 1:
                    raise NotImplementedError('no parser for team sheet style')
                    # crash here

                # search for player cells containing dotabuff link
                if tsparser in [0]:

                    for i, row in sheet.iterrows():
                        for j, val in enumerate(row.iloc):
                            
                            if j < 3:
                                # skip first 3 columns
                                continue
                            #if league['name'] == 'Wednesday' and j > 16:
                            #    # TEMP: iggy was hiding in the sheets
                            #    continue

                            # cell contains a dotabuff link, save info
                            # TODO: check if valid account link or ID instead
                            if '.com/' not in val:
                                continue

                            acc = extract_account_id(val)
                            info = {'account_id': acc}

                            # basic info
                            p = draft[draft['account_id'] == acc].iloc[0]
                            info['mmr'] = int(p['MMR'])
                            info['discord'] = p['Discord ID']
                            info['pos_pref'] = p[pos_idx: pos_idx + 5].values.astype(int).tolist()
                            info['alts'] = p['alts']

                            # country
                            info['country'] = get_player_data(p['account_id'])['country']

                            if league['type'] == 'auction':
                                #coins = sheet.iloc[i, j - 1]
                                coins = sheet.iloc[i, j + 1] # everybody's changing and I don't feel the same
                                try:
                                    coins = int(coins)
                                except:
                                    coins = 0
                                info['name'] = sheet.iloc[i, j - 2]
                                info['coins'] = coins
                            elif league['type'] == 'linear':
                                info['name'] = sheet.iloc[i, j - 2] # - 1 usually but -2 cz s28 spatzatura
                            players[(i, j)] = info

                    if players:
                        # group players by clustering the cells in the spreadsheet
                        cell_positions = np.array(list(players.keys()))
                        cell_clusters = DBS(eps = 2).fit(cell_positions).labels_
                        team_clusters = {t: cell_positions[np.where(cell_clusters == t)[0]] for t in np.unique(cell_clusters)}
                        teams = {t: [players[tuple(p)] for p in team] for t, team in team_clusters.items()}
                        teams2 = [{'name': p[0]['name'], 'players': p} for _, p in teams.items()]
                    else:
                        print('no players found')

                # lookup team tables by position
                elif tsparser in [1]:

                    teams = {}
                    for i, row in sheet.iterrows():
                        for j, val in enumerate(row.iloc):
                            if val == 'Coins':
                                # team table has 'Coins' on top right corner
                                team_table = sheet.iloc[i + 1: i + 6, [j - 3, j - 2, j]]
                                team = []
                                for _, (name, mmr, coins) in team_table.iterrows():
                                    if name == '':
                                        continue
                                    info = {}
                                    p = draft[draft['Name'] == name].iloc[0]
                                    info['account_id'] = p['account_id']
                                    info['mmr'] = int(mmr) # int(p['MMR'])
                                    info['discord'] = p['Discord ID']
                                    info['pos_pref'] = p[pos_idx: pos_idx + 5].values.astype(int).tolist()
                                    info['alts'] = p['alts']
                                    info['country'] = get_player_data(p['account_id'])['country']
                                    info['name'] = name
                                    if league['type'] == 'auction':
                                        info['coins'] = coins
                                    # add player to team
                                    team += [info]

                                if len(team) > 0:
                                    # team has players, add it
                                    teams[team[0]['name']] = team
                                print(team)
                    teams2 = [{'name': p[0]['name'], 'players': p} for _, p in teams.items()]

            print(season['name'], league['name'], division['name'])
            division['teams'] = teams2

# save data
with open(os.path.join(OUTPUT_PATH, FNAME + '_utf8.json'), 'w', encoding = 'utf-8') as f:
    json.dump(rd2l, f, indent = 4)
with open(os.path.join(OUTPUT_PATH, FNAME + '_utf16.json'), 'w', encoding = 'utf-16') as f:
    json.dump(rd2l, f, indent = 4, ensure_ascii = False)

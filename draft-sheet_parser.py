import requests, json, time, os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import *
from utilities import *

from sklearn.cluster import DBSCAN as DBS

INPUT_PATH = 'input'
OUTPUT_PATH = 'draft'
FNAME = 'rd2l_s29'

"""
Sheet styles:
0 unspecified, assume Owl sheets
1 Owl sheets: < S27: no hyperlinks, alts in a single cell
2 Moggoblin sheets: M14 S28: no hyperlinks, alts in "2nd account" "3rd account"
3 Moggoblin sheets: M15 S29: dotabuff urls hyperlinked, alts in "2nd account" "3rd account"
"""

with open(os.path.join(INPUT_PATH, FNAME + '.json'), 'r') as f:
    rd2l = json.load(f)

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:

            dsparser = 0
            if 'dsparser' in division:
                dsparser = division['dsparser']
            if dsparser > 3:
                raise NotImplementedError('no parser for sheet style')
                # crash here

            sheet = read_google_sheet(division['teamsheet'])
            # parse draft sheet
            if dsparser in [0, 1, 2]:
                draft = read_google_sheet(division['draftsheet'])
            elif dsparser in [3]:
                # hyperlinked cells for account url
                draft = read_google_sheet(division['draftsheet'], resolve_links = True)

            if dsparser in [0, 1]:
                # Owl sheets
                draft['account_id'] = draft['Dotabuff link'].apply(extract_account_id2)
                draft['alts'] = draft['Please list your alternate accounts'].apply(extract_account_ids)
            elif dsparser in [2, 3]:
                # Moggoblin sheets
                draft['account_id'] = draft['Dotabuff Link'].apply(extract_account_id2)
                draft['alts'] = draft[['Second account', 'Third account']].apply(list, axis = 1).astype(str).apply(extract_account_ids)
                draft = draft[draft['Activity check'].isin(['Yes', 'yes'])].copy()

            draft['accounts'] = draft.apply(lambda x: x['alts'] + [x['account_id']], axis = 1)

            pos_idx = draft.columns.searchsorted('Pos 1') + 1
            
            # search teamsheet for player cells
            players = {}
            for i, row in sheet.iterrows():
                for j, val in enumerate(row.iloc):
                    
                    if j < 3:
                        # skip first 3 columns
                        continue
                    
                    accs = extract_account_ids2(val)
                    if accs:
                        # cell contains a dotabuff link, save info
                        info = {'account_id': accs[0]}

                        # basic info
                        p = draft[draft['account_id'] == accs[0]].iloc[0]
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

                print(season['name'], league['name'], division['name'])
                division['teams'] = teams2

# save data
with open(os.path.join(OUTPUT_PATH, FNAME + '_utf8.json'), 'w', encoding = 'utf-8') as f:
    json.dump(rd2l, f, indent = 4)
with open(os.path.join(OUTPUT_PATH, FNAME + '_utf16.json'), 'w', encoding = 'utf-16') as f:
    json.dump(rd2l, f, indent = 4, ensure_ascii = False)

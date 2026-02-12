import requests, json, time, os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import rank2mmr
from utilities import datestr, read_google_sheet, rindex
from utilities2 import extract_account_id, extract_account_ids

from sklearn.cluster import DBSCAN as DBS

INPUT_PATH = 'input'
OUTPUT_PATH = 'draft'
FNAME = 'rd2l_s33'

"""
Sheet styles:
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

            # BYOB
            if league['type'] == 'byob':
                draft['account_id'] = draft['Account Link'].apply(extract_account_id)
                draft['alts'] = draft.apply(lambda x: [], axis = 1)
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

            # regular sheets
            else:

                ## read player list
                draft = read_google_sheet(division['signups'], resolve_links = True)
                draft = draft[draft['Activity check'].isin(['Yes', 'yes'])].copy() # sometimes people edit this field by hand

                # Owl and Moggoblin sheets ask for Dotabuff links for account ID
                link_col_options = ['dotabuff link', 'stratz link', 'account link']
                link_col = next(c for c in draft.columns if c.lower() in link_col_options) # get first match
                draft['account_id'] = draft[link_col].apply(extract_account_id)

                alts_col_options = ['second account', 'third account', 'please list your alternate accounts']
                alts_cols = [c for c in draft.columns if c.lower() in alts_col_options]
                alts = draft[alts_cols].fillna('').apply(' '.join, axis = 1)
                draft['alts'] = alts.apply(extract_account_ids)

                # cleanup
                draft['accounts'] = draft.apply(lambda x: x['alts'] + [x['account_id']], axis = 1)
                pos_idx = draft.columns.searchsorted('Pos 1') + 1
                
                ## search teamsheet for teams
                sheet = read_google_sheet(division['teamsheet'])
                sheet.fillna('', inplace = True)

                teams = {}
                for i, row in sheet.iterrows():
                    for j, val in enumerate(row.iloc):
                        if val == 'Player':
                            # team table has 'Player' on top left corner
                            # team table has 'Coins' on top right corner
                            # you might have to babysit these indexes if the sheet is different
                            # ex: if hidden columns were moved around
                            header = sheet.iloc[i, j: j + 4].to_list()
                            header = [h.lower() for h in header]
                            # sometimes the 'Player' keyword is repeated, skip what is not a table
                            if 'mmr' not in header:
                                continue
                            team_table = sheet.iloc[
                                i + 1: i + 6, # 5 below
                                j: j + 4 # 4 right (ignore 3rd)
                                ]
                            team = []
                            print(pd.DataFrame(team_table.values, columns = header))
                            # match the players by name, fill player info
                            for k, player_row in team_table.iterrows():
                                name = player_row[rindex(header, 'player')]
                                mmr = player_row[header.index('mmr')]
                                # don't add empty rows (not yet filled)
                                if name == '' or mmr == '':
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
                                    coins = player_row[header.index('coins')]
                                    try:
                                        coins = int(coins)
                                    except:
                                        coins = 0
                                    info['coins'] = coins
                                # add player to team
                                team += [info]

                            if len(team) > 0:
                                # team has players, add it
                                teams[team[0]['name']] = team
                            else:
                                print('No players found in team (hidden?)')

                # json-ing
                teams2 = [{'name': tn, 'players': p} for tn, p in teams.items()]

            # save it
            division['teams'] = teams2
            print('DONE:', season['name'], league['name'], division['name'])


# save data
with open(os.path.join(OUTPUT_PATH, FNAME + '.json'), 'w', encoding = 'utf-16') as f:
    json.dump(rd2l, f, indent = 4, ensure_ascii = False)

import requests, json, time, os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import *

from sklearn.cluster import DBSCAN as DBS

INPUT_PATH = 'input'
OUTPUT_PATH = 'output'
FNAME = 'rd2l_s28'

def read_google_sheet(url):
    url2 = url[:url.index('/edit')] + '/export?format=csv&' + url[url.index('gid='):]
    return pd.read_csv(url2)

with open(os.path.join(INPUT_PATH, FNAME + '.json'), 'r') as f:
    rd2l = json.load(f)

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:
            sheet = read_google_sheet(division['teamsheet'])
            
            # parse draft sheet
            draft = read_google_sheet(division['draftsheet'])

            if 'dsparser' not in division or division['dsparser'] == 1:
                # Owl sheets
                draft['account_id'] = draft['Dotabuff link'].apply(extract_account_id2)
                draft['alts'] = draft['Please list your alternate accounts'].apply(extract_account_ids)
            elif division['dsparser'] >= 2:
                # Moggoblin sheets
                draft['account_id'] = draft['Dotabuff Link'].apply(extract_account_id2)
                draft['alts'] = draft[['Second account', 'Third account']].apply(list, axis = 1).astype(str).apply(extract_account_ids)
                draft = draft[draft['Activity check'] == 'Yes'].copy()

            draft['accounts'] = draft.apply(lambda x: x['alts'] + [x['account_id']], axis = 1)

            pos_idx = draft.columns.searchsorted('Pos 1')
            
            # search sheet for player cells
            players = {}
            for i, row in sheet.iterrows():
                for j, val in enumerate(row.iloc):
                    accs = extract_account_ids2(val)
                    if accs:
                        # row contains a dotabuff link, save info
                        info = {'account_id': accs[0]}

                        # basic info
                        p = draft[draft['account_id'] == accs[0]].iloc[0]
                        info['mmr'] = int(p['MMR'])
                        info['discord'] = p['Discord ID']
                        #info['pos_pref'] = p[pos_idx + 1: pos_idx + 6].values.astype(int).tolist()
                        # FIXME: why +1?
                        info['pos_pref'] = p[pos_idx: pos_idx + 5].values.astype(int).tolist()
                        info['alts'] = p['alts']

                        # top 3 heroes
                        params = {
                            'date': 90,
                            # add 'significant': 0 to include turbo games
                            }
                        matches = [m for a in accs for m in get_player_matches(a, **params)]
                        matches = [m for m in matches if m != 'error']
                        matches = sorted(matches, key = lambda x: x['start_time'], reverse = True)
                        heroes = [m['hero_id'] for m in matches]
                        u, c = np.unique(heroes, return_counts = True)
                        info['top3'] = u[np.argsort(c)][::-1][:3].tolist()

                        # country
                        info['country'] = get_player_data(p['account_id'])['country']

                        if league['type'] == 'auction':
                            coins = sheet.iloc[i, j - 1]
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


# liquipedia teams
template = """{{{{TeamCard
|team={}
|preview=
|ref=
|image=Ti9 teamcard logo.png
|p1flag={}|p1={}|p1id={}
|p2flag={}|p2={}|p2id={}
|p3flag={}|p3={}|p3id={}
|p4flag={}|p4={}|p4id={}
|p5flag={}|p5={}|p5id={}
}}}}"""

# generate liquipedia output
def liquipedia_teams_str(teams, template):
    out = []
    for team in teams:
        frmt = [team['name']]
        for player in team['players']:
            frmt += [player['country'], player['name'], player['account_id']]
        out += [template.format(*frmt)]
    out = '\n{{box|break|padding=2em}}\n'.join(out)
    return out

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:
            print(season['name'], league['name'], division['name'])
            print(liquipedia_teams_str(division['teams'], template), end = '\n\n\n')

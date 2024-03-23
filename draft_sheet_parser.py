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

"""
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
"""
with open(os.path.join(OUTPUT_PATH, FNAME + '_utf16.json'), 'r', encoding = 'utf-16') as f:
    rd2l = json.load(f)


def team_roles(team, g = 2):
    """assign roles to players by preference and mmr"""
    tim = pd.DataFrame(team['players'])
    mi = tim['mmr'].min()
    ma = tim['mmr'].max()
    mmr = (tim['mmr'] - mi) / (ma - mi)
    # mmr difference to gold-priority factor
    # set to 0 to use player role preference only
    # set to big number to use mmr for roles (i.e. pos 1 highest mmr)
    # reasonable values for g are 1 to 4
    mmr_gpf = g * np.outer(mmr, [1, .8, .6, .4, .2]) # todo: maybe .3 .3 for supports?
    pos = ['p1', 'p2', 'p3', 'p4', 'p5']
    tim[pos] = tim['pos_pref'].apply(pd.Series).add(mmr_gpf, axis = 0)
    roles = []
    for p in pos:
        for i in tim[p].sort_values(ascending = False).index:
            if i not in roles:
                roles += [i]
                break
    #happ = [] # find permutation with best role satisfaction
    # for test in itertools.permmutations(range(5)):
    #tim['pos'] = roles
    return roles

# liquipedia teams
template = """{{{{TeamCard
|team={}
|preview=
|ref=
|image=Ti9 teamcard logo.png
{}
|inotes={}
}}}}"""

px = '|p{0}flag={1}|p{0}={2}|p{0}id={3}'
db = '{{{{cite web|url=https://www.dotabuff.com/players/{}|title={}}}}}'

teamsep = '\n{{box|break|padding=2em}}\n'

# generate liquipedia output
def liquipedia_team_str(team):
    roles = team_roles(team)
    px_fill = []
    db_fill = []
    for role in range(5):
        player = team['players'][roles[role]]
        px_fill += [px.format(role + 1, player['country'], player['name'], player['account_id'])]
        db_fill += [
            db.format(player['account_id'], player['name']) +
            ''.join([db.format(a, k + 2) for k, a in enumerate(player['alts'])])
            ]
    return template.format(team['name'], '\n'.join(px_fill), ' '.join(db_fill))

def liquipedia_teams_str(teams):
    return teamsep.join([liquipedia_team_str(team) for team in teams])

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:
            print(season['name'], league['name'], division['name'])
            print(liquipedia_teams_str(division['teams']), end = '\n\n\n')

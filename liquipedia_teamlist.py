import os, json
import requests, time
import pandas as pd
import numpy as np

INPUT_PATH = 'draft'
OUTPUT_PATH = ''
FNAME = 'rd2l_m17'

with open(os.path.join(INPUT_PATH, FNAME + '.json'), 'r', encoding = 'utf-16') as f:
    rd2l = json.load(f)

# liquipedia teams
begin = '{{TeamParticipants|showplayerinfo=true\n'
end = '\n}}'

template = """
|{{{{Opponent|{0}
|aliases={0}
|players={{{{Persons
{1}
}}}}
|ref=
|image=
|notes={{{{Notes
{2}
}}}}
}}}}
"""

px = '|{{{{Person|role={0}|flag={1}|{2}|id={3}}}}}'
nt = '|{{{{Notes|{0}}}}}'
db = '{{{{cite web|url=https://www.opendota.com/players/{0}|title={1}}}}}'

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

# generate liquipedia output
def liquipedia_team_str(team):
    roles = team_roles(team)
    px_fill = []
    nt_fill = []
    for role in range(5):
        player = team['players'][roles[role]]
        name = player['name']
        country = player['country']
        acc = player['account_id']
        px_fill += [px.format(role + 1, country, name, acc)]
        db_fill = [db.format(acc, name)]
        for k, a in enumerate(player['alts']):
            name2 = f'{name} {k + 2}'
            db_fill += [db.format(a, name2)]
        db_text = ''.join(db_fill)
        nt_fill += [nt.format(db_text)]
    px_text = '\n'.join(px_fill)
    nt_text = '\n'.join(nt_fill)
    return template.format(team['name'], px_text, nt_text)

def liquipedia_teams_str(teams):
    return begin + ''.join([liquipedia_team_str(team) for team in teams]) + end

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:
            print(season['name'], league['name'], division['name'])
            print(liquipedia_teams_str(division['teams']), end = '\n\n\n')

import requests, json, time, os
import pandas as pd
import numpy as np

INPUT_PATH = 'draft'
OUTPUT_PATH = ''
FNAME = 'rd2l_shakira2024'

with open(os.path.join(INPUT_PATH, FNAME + '_utf16.json'), 'r', encoding = 'utf-16') as f:
    rd2l = json.load(f)

# liquipedia teams
template = """{{{{TeamCard
|team={}
|preview=
|ref=
|image=
{}{}
}}}}"""

px = '|p{0}flag={1}|p{0}={2}|p{0}id={3}|p{0}preview=https://www.dotabuff.com/players/{3}'
db = '{{{{cite web|url=https://www.dotabuff.com/players/{}|title={} {}}}}}'

teamsep = '\n{{box|break|padding=2em}}\n'

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
    db_fill = []
    for role in range(5):
        player = team['players'][roles[role]]
        px_fill += [px.format(role + 1, player['country'], player['name'], player['account_id'])]
        db_text = ''
        for k, a in enumerate(player['alts']):
            db_text += db.format(a, player['name'], k + 2)
        if db_text != '':
            db_fill += [db_text]
    inotes = ''
    if len(db_fill) > 0:
        inotes = '\n|inotes=' + ' '.join(db_fill)
    return template.format(team['name'], '\n'.join(px_fill), inotes)

def liquipedia_teams_str(teams):
    return teamsep.join([liquipedia_team_str(team) for team in teams])

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:
            print(season['name'], league['name'], division['name'])
            print(liquipedia_teams_str(division['teams']), end = '\n\n\n')

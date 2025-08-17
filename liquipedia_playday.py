import os, json
import pandas as pd
import numpy as np
from d2tools.api import get_league_matches
from liquipedia_map import gen_map_text
from utilities import datetoseconds, datestr, season_info_get, season_info_get_teams

## input
search = {
    'org': 'rd2l',
    'tournament': 'main', # mini main side shakira ...
    'season': '31',
    'league': 'Sunday', # Wednesday Sunday
    'division': '1'
    }

timezone = 'CET'
start_time_str = 'August 17 2025 - 16:00'
start_time = datetoseconds(start_time_str, 'CET')
end_time = 2000000000

bestof = 3
force = True
save = True

# TODO: automate filling this
series_scheduled = [
    ('Leiya', 'Aty'),
    ('prime skiter', 'Tsenme'),
    ('Exy-', 'Unseelie'),
    ]

# Unseelie prime skiter Tsenme Exy- Aty DJDuese Cvaekt Leiya
# Muko ClapTiq Faith Lanfe4r Drregron Lewis Potentiallyyouruncle Wiolarz
# Kiritoya- canin Beno FTG Jam Apple YNWA baul Wiolarz Lanfe4r

# teams
encoding = 'utf-16'

## main

# read league info
ttag_lookup = {'main': 's', 'mini': 'm'}
tour = search['tournament'].lower()
ttag = ttag_lookup.get(tour, tour)
encoding2 = encoding.replace('-', '')

team_info_str = search['org'], ttag, search['season'], encoding2
team_info_path = os.path.join('draft', '{}_{}{}_{}.json'.format(*team_info_str))

with open(team_info_path, encoding = encoding) as f:
    season_info = json.load(f)

league_id = season_info_get(season_info, seasons = search['season'], leagues = search['league'])['id']
teams = season_info_get_teams(season_info, **search)
team_acc = {t['name']: [a for p in t['players'] for a in [p['account_id']] + p['alts']] for t in teams}

# get league matches
matches = get_league_matches(league_id, force = force)
players = [pd.DataFrame(m['players']).groupby('team_number')['account_id'].agg(list) for m in matches]
keys = ['match_id', 'start_time', 'radiant_team_id', 'dire_team_id']
data = [{k: v for k, v in m.items() if k in keys} for m in matches]

def find_team(account_ids, min_players = 3):
    found = np.array([sum([str(a) in acc for a in account_ids]) for n, acc in team_acc.items()])
    try:
        return teams[np.where(found >= min_players)[0][0]] # take first team
    except:
        raise IndexError('Team not found')

# keep those matching a team in draft sheet
filtered = []
sides = {0: 'radiant', 1: 'dire'}
for i in range(len(matches)):
    for k, v in sides.items():

        data[i]['{}_team_accs'.format(v)] = ', '.join(str(a) for a in players[i][k])

        try:
            name = find_team(players[i][k], 3)['name']
        except:
            try:
                name = find_team(players[i][k], 2)['name']
            except:
                try:
                    name = find_team(players[i][k], 1)['name'] # despair
                except:
                    continue

        data[i]['{}_team_name'.format(v)] = name
        filtered += [i]

# group matches by date and teams
data = pd.DataFrame(np.array(data)[np.unique(filtered)].tolist())
data = data[(data['start_time'] > start_time) & (data['start_time'] < end_time)]
data['series_name'] = data.apply(lambda x: ', '.join(sorted([x['radiant_team_name'], x['dire_team_name']])), axis = 1)

# generate list of series that were actually played
# todo: make below section better
series_played = {}
for i, d in enumerate(data.groupby('series_name').agg(list).iloc):
    series = pd.DataFrame({k: d[k] for k in d.index})
    series.sort_values('start_time', inplace = True)
    team1 = series.iloc[0]['dire_team_name'] # order not important for now
    team2 = series.iloc[0]['radiant_team_name']
    series_played[(team1, team2)] = series.copy()
    series_played[(team2, team1)] = series.copy()

# start filling in text
template1 = """{{{{Match
|bestof={}
|winner=
|opponent1={{{{TeamOpponent|{}}}}}
|opponent2={{{{TeamOpponent|{}}}}}
"""
template2 = """|date={}{}
|finished={}
|twitch=
"""
template3 = """|team1side=
|t1h1=|t1h2=|t1h3=|t1h4=|t1h5=
|t1b1=|t1b2=|t1b3=|t1b4=|t1b5=|t1b6=|t1b7=
|team2side=
|t2h1=|t2h2=|t2h3=|t2h4=|t2h5=
|t2b1=|t2b2=|t2b3=|t2b4=|t2b5=|t2b6=|t2b7=
|length=|winner="""

# start filling in text
series_texts = []
for ss in series_scheduled:
    if ss not in series_played:
        series = None
    else:
        series = series_played[ss]
    
    text = ''

    # team info
    text += template1.format(bestof, ss[0], ss[1])

    # date and time
    if series is not None:
        series_time = datestr(series['start_time'].iloc[0], timezone)
        finished = '1'
    else:
        series_time = ''
        finished = ''

    text += template2.format(series_time, '{{abbr/' + timezone + '}}', finished)

    # vods and match IDs
    for i in range(bestof):
        text += '|vodgame{}=\n'.format(i + 1)
    for i in range(bestof):
        text += '|matchid{}='.format(i + 1)
        if series is not None and i < len(series):
            text += str(series.iloc[i]['match_id']) + '\n'
        else:
            text += '\n'

    # match info
    for i in range(bestof):
        text += '|map{}={{{{Map'.format(i + 1)
        if series is not None and i < len(series):
            match_id = series.iloc[i]['match_id']
            # check who is radiant or dire
            if series.iloc[i]['radiant_team_name'] == ss[0]:
                team1_side = 'radiant'
            else:
                team1_side = 'dire'
            # try to get Map
            try:
                text += gen_map_text(match_id, team1 = team1_side)
            except:
                text += '\n' + template3
        else:
            text += '\n' + template3
        text += '\n}}\n'

    # closing
    text += '}}'
    series_texts += [text]

# print it
print('\n\n\n')
for i, txt in enumerate(series_texts):
    #print("|M{0}header=\n|M{0}=".format(i + 1) + txt)
    print("|M{0}=".format(i + 1) + txt)

# save data
if save:
    fname = 's{}_{}_div{}_{}.csv'.format(
        search['season'],
        search['league'][:3].lower(),
        search['division'],
        datestr(start_time, frmt = '%Y-%m-%d')
        )
    data.to_csv(os.path.join('playday', fname))

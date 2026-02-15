import os, json
import pandas as pd
import numpy as np
import itertools
import pyperclip
from utilities import alphanumeric, season_info_get, season_info_get_teams
from schedule import schedule_get_matches

## input
search = {
    'org': 'rd2l',
    'tournament': 'main', # mini main side shakira ...
    'season': '33',
    'league': 'Sunday', # Wednesday Sunday
    'division': '3'
    }

start_time = 'February 11 2026 - 20:00' # first match day and time
weeks = 5 # number of groupstage weeks
split = 1 # split into n groups # TODO
bestof = 2

# datetime settings
timezone = 'CET'
frmt = '%B %d %Y - %H:%M'
st = pd.to_datetime(start_time).tz_localize('CET')


## main

# read existing matches first
playdays = []
for week in range(1, weeks + 1):
    series = schedule_get_matches(week, **search)
    series = tuple(t for s in series for t in s) # unpack
    if all([''.join(s) == ''for s in series]):
        # empty week, no schedule yet
        continue
    print('week', week, ':\n', series)
    playdays += [series]

# temp fix for wed split in 2 groups
#playday = [('iggy', 'HungryBrowny', 'm.', 'FTG', 'NERK', 'Rinkugod')]
#playday = [('Cooke', 'Jam Apple YNWA', 'Fumblegod', 'Harmani', 'zRomep', 'Qso')]

# read league info
ttag_lookup = {'main': 's', 'mini': 'm'}
tour = search['tournament'].lower()
ttag = ttag_lookup.get(tour, tour)
team_info_str = search['org'], ttag, search['season']
team_info_path = os.path.join('draft', '{}_{}{}.json'.format(*team_info_str))

with open(team_info_path, encoding = 'utf-16') as f:
    season_info = json.load(f)

league_id = season_info_get(season_info, seasons = search['season'], leagues = search['league'])['id']
teams = [t['name'] for t in season_info_get_teams(season_info, **search)]

# temp fix for wed split in 2 groups
#teams = playday[0]

# round robin is to not repeat any of all past series
all_series = []
for p in playdays:
    all_series += [set(s) for s in zip(p[::2], p[1::2])] # repack
for p in list(itertools.permutations(teams)):
    series = [set(s) for s in zip(p[::2], p[1::2])]
    if all([s not in all_series for s in series]):
        playdays += [p]
        all_series += series

# start filling in text
template1 = """{{{{Match
|bestof={}
|winner=
|opponent1={{{{TeamOpponent|{}}}}}
|opponent2={{{{TeamOpponent|{}}}}}
"""
template2 = """|date={}{}
|finished=
|twitch=
"""
template3 = """|team1side=
|t1h1=|t1h2=|t1h3=|t1h4=|t1h5=
|t1b1=|t1b2=|t1b3=|t1b4=|t1b5=|t1b6=|t1b7=
|team2side=
|t2h1=|t2h2=|t2h3=|t2h4=|t2h5=
|t2b1=|t2b2=|t2b3=|t2b4=|t2b5=|t2b6=|t2b7=
|length=|winner="""
template4 = """{{{{Matchlist|id={}|title={}
{}
}}}}
"""
template5 = """==Matches==
{{{{box|start|padding=2em|max-width=1000px}}}}
{}{{{{box|end}}}}"""

full_text = []
schedule = []
for w, p in enumerate(playdays[:weeks]):
    week = w + 1
    series = [tuple(s) for s in zip(p[::2], p[1::2])]

    # date and time
    dt = st + pd.tseries.offsets.Week(n = w)
    series_time = dt.strftime(frmt)

    # add Match or Match2 for each series
    series_texts = []
    for k, ss in enumerate(series):
    
        text = '|M{0}header=\n|M{0}='.format(k + 1)

        # team info
        text += template1.format(bestof, ss[0], ss[1])
        # date and time
        text += template2.format(series_time, '{{abbr/' + timezone + '}}')

        # vods and match IDs
        for i in range(bestof):
            text += '|vodgame{}=\n'.format(i + 1)
        for i in range(bestof):
            text += '|matchid{}=\n'.format(i + 1)

        # match info
        for i in range(bestof):
            text += '|map{}={{{{Map'.format(i + 1)
            text += '\n' + template3
            text += '\n}}\n'

        # closing
        text += '}}'

        series_texts += [text]

    schedule += [{
        'week': week,
        'matches': [
                {
                    'left_top': s[0],
                    'right_bot': s[1],
                }
            for s in series
            ]
        }]

    # print it
    suffix = { 1 : 'st', 2 : 'nd', 3 : 'rd' }.get(dt.day % 10, 'th')
    playday_date = dt.strftime('%B %d').replace(' 0', ' ') + suffix
    list_id = alphanumeric(10)
    full_text += [template4.format(list_id, playday_date, '\n'.join(series_texts))]

full_text = template5.format('{{box|break|padding=2em}}\n'.join(full_text))

print(full_text)
pyperclip.copy(full_text)
print('Liquipedia text copied to clicpboard!')

print('Below is the .json export')
print(json.dumps(schedule, indent = 4))

import os, json
import pandas as pd
import numpy as np
from d2tools.api import get_league_matches, get_match
from utilities import datetoseconds, season_info_get, season_info_get_teams
from schedule import schedule_get_matches

## input
search = {
    'org': 'rd2l',
    'tournament': 'main', # mini main side shakira ...
    'season': '31',
    'league': 'Sunday', # Wednesday Sunday
    'divisions': ['1', '2'],
    }

fantasy_table = {
    'kills': 0.3,
    'deaths': -0.3, # +3
    'assists': 0.15,
    'last_hits': 0.003,
    'gold_per_min': 0.002,
    'towers_killed': 1.0,
    'roshans_killed': 1.0,
    'obs_placed': 0.5,
    'camps_stacked': 0.5,
    'rune_pickups': 0.25,
    'firstblood_claimed': 4.0,
    'stuns': 0.05,
}

fantasy_keep_bestof = 2 # if BO3, keep 2 best games
week = 1

# extra settings

start_time_str = 'July 27 2025 - 16:00'
start_time = datetoseconds(start_time_str, 'CET')
end_time = 2000000000

force = True
save = True

encoding = 'utf-16'

## main

# read schedule for series
series_scheduled = []
for division in search['divisions']:
    series_scheduled += schedule_get_matches(week, division = division, **search)

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

# read list of players in each team
teams = []
for division in search['divisions']:
    teams += season_info_get_teams(season_info, division = division, **search)

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

# get fantasy stats for each match and save to file
fstats_all = []
for match_id in data['match_id']:
    fstats = pd.DataFrame()
    match = get_match(match_id)
    for idx, player in enumerate(match['players']):
        a_id = player['account_id']
        for k, v in fantasy_table.items():
            fstats.loc[a_id, k] = player.get(k, 0) * v

    fstats['deaths'] += 3
    fstats['deaths'] = fstats['deaths'].apply(lambda x: max(x, 0))
    fstats['total'] = fstats[fantasy_table.keys()].sum(axis = 1)
    fstats.to_csv(os.path.join('fantasy', 'matches', 'fantasy_{}.csv'.format(match_id)))
    fstats['match_id'] = match_id
    fstats_all += [fstats]

# combine fantasy stats and keep best n scores
fdata = pd.concat(fstats_all).reset_index(names = 'account_id')

def is_top_n(arr, n):
    arr = np.array(arr)
    idx = np.argsort(arr)[-n:]
    res = np.zeros(arr.shape)
    res[idx] = 1
    return res.astype(bool)

best_n = fdata.groupby('account_id')['total'].transform(is_top_n, fantasy_keep_bestof)
fdata = fdata[best_n]

ftk = list(fantasy_table.keys()) + ['total']
fplayers = fdata.groupby('account_id')[ftk].apply(sum)
fplayers = fplayers.round(3)

# save player fantasy data
fname = 's{}_{}_w{}.csv'.format(
    search['season'],
    search['league'][:3].lower(),
    week,
    )
if save:
    fplayers.to_csv(os.path.join('fantasy', 'players', fname))

# read participant picks for this week
draft = pd.read_csv(os.path.join('fantasy', 'draft', fname))

participant_picks = {}
for idx, row in draft.iterrows():
    name = row['Name']
    picks = row[draft.columns[1: 6]]
    picks = [p.lower().strip() for p in picks.values]
    participant_picks[name] = picks

# get all player accounts
player_pool = {}
for t in teams:
    for p in t['players']:
         player = p['name'].lower().strip()
         accs = [p['account_id']] + p['alts']
         player_pool[player] = accs

# get accounts of participant teammates if they are playing
teammates = {}
for part in participant_picks:
    name = part.lower().strip()
    if name in player_pool:
        acc_id = player_pool[name][0]
        for team_name, accs in team_acc.items():
            if acc_id in accs:
                teammates[name] = accs

# match names with accounts
participant_picks_account_ids = {}
for part, picks in participant_picks.items():
    account_ids = []
    for pick in picks:
        found = False
        if pick in player_pool:
            account_ids += [player_pool[pick]]
            found = True
        elif '/' in pick:
            pick2 = pick.split('/')
            for p in pick2:
                if p in player_pool:
                    account_ids += [player_pool[pick]]
                    found = True
                    break
        if not found:
            print('Missing', pick, 'for', part)
    participant_picks_account_ids[part] = account_ids

# find how many points each participant pick got
participant_points = {}
for part, account_ids in participant_picks_account_ids.items():
    # give 0 points if you picked your teammate
    name = part.lower().strip()
    tmates = teammates.get(name, [])
    # collect for each player entry
    fpoints = []
    for accounts in account_ids:
        fpts = [] # sum for each account
        for a in accounts:
            if int(a) in fplayers.index:
                fpts += [fplayers.loc[int(a)]['total']]
        if len(fpts) == 0:
            print('player', accounts, 'did not play')
            fpts = [0]
        if any([a in tmates for a in accounts]):            
            print('participant', part, 'picked his teammate', accounts)
            fpts = [0]
        fpoints += [sum(fpts)]
    participant_points[part] = fpoints

ppts = pd.DataFrame(participant_points).T.reset_index()

# collect results for each participant
result = pd.DataFrame()
result['name'] = draft['Name']
result['timestamp'] = draft.iloc[:, 0]
for i in range(1, 6):
    result[f'pick_{i}'] = draft.iloc[:, i]
    result[f'pts_{i}'] = ppts.iloc[:, i]
result['total'] = result.iloc[:, [3, 5, 7, 9, 11]].sum(axis = 1).round(3)

if save:
    result.to_csv(os.path.join('fantasy', 'participants', fname))

# calculate total
files = os.listdir(os.path.join('fantasy', 'participants'))
results = pd.concat([pd.read_csv(os.path.join('fantasy', 'participants', f)) for f in files])
total_result = results.groupby('name')['total'].sum().sort_values(ascending = False).round(2)

if save:
    fname2 = 's{}_{}.csv'.format(
        search['season'],
        search['league'][:3].lower(),
    )
    total_result.to_csv(os.path.join('fantasy', fname2))

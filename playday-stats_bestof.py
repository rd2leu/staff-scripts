import os, json
import pandas as pd
import numpy as np
from utilities import season_info_get_teams

## input
search = {
    'org': 'rd2l',
    'season': '30',
    'league': 'Wednesday', # Sunday Wednesday
    'division': '1'
    }

encoding = 'utf-16'
encoding2 = 'utf16' # FIXME

## main

# read league info
team_info_str = search['org'], search['season'], encoding2
team_info_path = os.path.join('draft', '{}_s{}_{}.json'.format(*team_info_str))

with open(team_info_path, encoding = encoding) as f:
    season_info = json.load(f)

teams = season_info_get_teams(season_info, **search)
team_acc = {t['name']: [a for p in t['players'] for a in [p['account_id']] + p['alts']] for t in teams}

players = pd.DataFrame([p | {'team': t['name']} for t in teams for p in t['players']])

# read stats
stats_str = 's{}_{}_div{}'.format(search['season'], search['league'][:3].lower(), search['division'])
stats_path = [p for p in os.listdir('stats') if p.startswith(stats_str)][-1]
stats = pd.read_csv(os.path.join('stats', stats_path), index_col = 0)

## generate best-of stats

def get_player_name(account_id):
    try:
        return players[players['account_id'] == str(account_id)]['name'].values[0]
    except:
        return str(account_id)

def plot_overall_stats(title, account_ids, values):
    print(title)
    for i, (a, v) in enumerate(zip(account_ids, values)):
        print('rank', i + 1, get_player_name(a), v)
    print()

# most total sum of player things
things = [
    'obs_placed', 'sen_placed', 'camps_stacked', 'rune_pickups',
    'firstblood_claimed', 'towers_killed', 'roshans_killed', 'stuns', 'pings',
    'kills', 'deaths', 'assists', 'last_hits', 'denies',
    'net_worth', 'hero_damage', 'tower_damage', 'hero_healing',
    'neutral_kills', 'courier_kills', 'observer_kills',
    'buyback_count', 'life_state_dead', 'bought_rapier', 'bought_consumables',
    'used_blood_grenade', 'used_enchanted_mango', 'used_smoke_of_deceit',
    'used_blink', 'used_armlet', 'used_revenants_brooch', 'used_pirate_hat',
    'trees_quelled', 'runes_bounty', 'runes_wisdom', 'runes_6min',
    'blood_inflicted', 'lotuses_stolen', 'uses_high_five',
    #'uses_portal', # bugged
    'cosmetics_count', 'cosmetics_immortals',

    'bought_tranquil_boots', 'bought_travel_boots', 'bought_travel_boots_2',
    'bought_phase_boots', 'bought_boots', 'bought_arcane_boots', 'bought_power_treads',
    'bought_guardian_greaves', 'bought_boots_of_bearing', 'bought_force_boots',
    'bought_wind_lace', 'bought_tpscroll', 'bought_slippers', 'bought_boots_of_elves',

    'used_travel', 'used_tpscroll',
    ]
##things = ['life_state_dead', 'lotuses_stolen', 'trees_quelled', 'runes_6min']
##things = ['kills', 'courier_kills', 'roshans_killed']
##things = ['denies']
##things = ['used_travel', 'tpscroll']
##things = ['tower_damage']
##things = ['cosmetics_count']

for thing in things:
    ids = stats.groupby('account_id')[thing].sum().sort_values(ascending = False)[:4]
    plot_overall_stats('Most {}'.format(thing), ids.keys(), ids.values)
  
# most player thing in a game
things = [
    'duration', 'obs_placed', 'sen_placed', 'camps_stacked', 'rune_pickups',
    'firstblood_claimed', 'teamfight_participation', 'towers_killed',
    'roshans_killed', 'stuns', 'pings', 'hero_id', 'kills', 'deaths',
    'assists', 'last_hits', 'denies', 'gold_per_min', 'xp_per_min',
    'net_worth', 'hero_damage', 'tower_damage', 'hero_healing', 'kda',
    'neutral_kills', 'courier_kills', 'observer_kills', 'ancient_kills',
    'buyback_count', 'life_state_dead', 'max_hero_hit', 'max_mins_no_lh',
    'avg_obs_dur', 'repeated_obs', 'bought_rapier', 'bought_consumables',
    'used_blood_grenade', 'used_enchanted_mango', 'used_smoke_of_deceit',
    'used_blink', 'used_armlet', 'used_revenants_brooch', 'used_pirate_hat',
    'trees_quelled', 'runes_bounty', 'runes_wisdom', 'runes_6min',
    'kill_streak', 'blood_inflicted', 'lotuses_stolen', 'uses_high_five',
    'cosmetics_count', 'cosmetics_immortals'
    ]
##things = ['max_mins_no_lh', 'used_armlet', 'used_enchanted_mango']
##things = ['denies']
##things = ['cosmetics_count']

for thing in things:
    print('Game with most', thing)
    top = stats.loc[stats[thing].sort_values(ascending = False)[:5].index]
    top['name'] = top['account_id'].apply(get_player_name)
    print(top[['match_id', 'name', 'series_name', 'win', thing]], end = '\n\n')

# game with most things
things = [
    'duration', 'obs_placed', 'sen_placed', 'camps_stacked',
    'roshans_killed', 'bought_rapier', 'kill_streak'
    ]
##things = ['denies']
##things = ['cosmetics_count']

for thing in things:
    print('Game with most', thing)
    grp = stats.groupby('match_id')
    top = grp[thing].max().sort_values(ascending = False)[:3]
    res = grp[['series_name', 'account_id', 'win', 'dire_team_name', 'radiant_team_name', 'isRadiant']].first().loc[top.index]
    res[thing] = top
    res['win'] = res['win'].astype(bool)
    res['name'] = res['account_id'].apply(get_player_name)
    res['winner'] = res.apply(lambda x: x['dire_team_name'] if (x['isRadiant'] ^ x['win']) else x['radiant_team_name'], axis = 1)
    #print(res[['series_name', 'account_id', 'winner', thing]], end = '\n\n')
    print(res[['name', 'win', thing]], end = '\n\n')

# game with most total things
things = [
    'duration', 'obs_placed', 'sen_placed', 'camps_stacked',
    'roshans_killed', 'bought_rapier', 'kill_streak', 'courier_kills',
    'lotuses_stolen', 'uses_high_five',
    'cosmetics_count', 'cosmetics_immortals'
    ]
##things = ['cosmetics_count', 'uses_high_five']
##things = ['denies']
##things = ['cosmetics_count']

for thing in things:
    print('Game with most total', thing)
    grp = stats.groupby('match_id')
    top = grp[thing].sum().sort_values(ascending = False)[:3]
    res = grp[['series_name', 'win', 'dire_team_name', 'radiant_team_name', 'isRadiant']].first().loc[top.index]
    res[thing] = top
    res['win'] = res['win'].astype(bool)
    res['winner'] = res.apply(lambda x: x['dire_team_name'] if (x['isRadiant'] ^ x['win']) else x['radiant_team_name'], axis = 1)
    print(res[['series_name', 'winner', thing]], end = '\n\n')

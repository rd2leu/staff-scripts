import os, json
import pandas as pd
import numpy as np
import scipy.stats as st
from d2tools.api import *
from d2tools.utilities import *

## input
search = {'season': '28',
          'league': 'Wednesday', # Sunday Wednesday
          'division': '1'}

timezone = 'CET'
start_time_str = 'December 24 2023 - 16:00'
start_time = datetoseconds(start_time_str, 'CET')
end_time = 2000000000

bestof = 3
force = False

team_info_path = os.path.join('draft', 'rd2l_s28_utf16.json')

## main
def find_matching(array, substring, lower = True, sep = ' '):
    if lower:
        arr = np.array([v.lower() for v in array])
        sub = str(substring).lower()
    else:
        arr = np.array(array)
        sub = str(substring)
    idx = len(arr)
    for i, s in enumerate(arr):
        s_ = s.split(sep)
        if all([k in s_ for k in sub.split(sep)]):
            idx = i
            break
    return idx

# find league info
with open(team_info_path, encoding = 'utf-16') as f:
    season_info = json.load(f)

seasons = [s['name'] for s in season_info['seasons']]
s_idx = find_matching(seasons, search['season'])

leagues = [l['name'] for l in season_info['seasons'][s_idx]['leagues']]
l_idx = find_matching(leagues, search['league'])
league_id = season_info['seasons'][s_idx]['leagues'][l_idx]['id'] # 14871

divisions = [d['name'] for d in season_info['seasons'][s_idx]['leagues'][l_idx]['divisions']]
d_idx = find_matching(divisions, search['division'])

teams = season_info['seasons'][s_idx]['leagues'][l_idx]['divisions'][d_idx]['teams']
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
data['series_name'] = data.apply(lambda x: ' vs '.join(sorted([x['radiant_team_name'], x['dire_team_name']])), axis = 1)

def get_match_player_stats(match_id):
    """player stats for single match"""
    pstats = pd.DataFrame()
    pstats_keys = [
        'win', 'isRadiant', 'duration',
        'obs_placed', 'sen_placed', 'camps_stacked', 'rune_pickups',
        'firstblood_claimed', 'teamfight_participation', 'towers_killed',
        'roshans_killed', 'stuns', 'pings', 'hero_id', 'kills', 'deaths',
        'assists', 'last_hits', 'denies', 'gold_per_min', 'xp_per_min',
        'net_worth', 'hero_damage', 'tower_damage', 'hero_healing', 'kda',
        'neutral_kills', 'courier_kills', 'observer_kills', 'ancient_kills',
        'buyback_count', 'life_state_dead',
        ]

    match = get_match(match_id)
    for idx, player in enumerate(match['players']):
        
        a_id = player['account_id']
        pstats.loc[a_id, 'match_id'] = match_id

        for k in pstats_keys:
            pstats.loc[a_id, k] = player.get(k, None)

        if any([k not in player for k in pstats_keys]):
            # abort early
            continue

        # biggest damage instance
        pstats.loc[a_id, 'max_hero_hit'] = player['max_hero_hit']['value']

        # most minutes without a lasthit
        pstats.loc[a_id, 'max_mins_no_lh'] = st.mode(player['lh_t'], keepdims = False).count

        # observer stats
        obs = pd.concat([
            pd.DataFrame(player['obs_log']),
            pd.DataFrame(player['obs_left_log'])
            ])
        pstats.loc[a_id, 'avg_obs_dur'] = None
        pstats.loc[a_id, 'repeated_obs'] = None
        if len(obs) > 0:
            obs_alive = obs.groupby('ehandle')['time'].apply(np.diff)
            obs_alive = obs_alive[obs_alive.apply(len).astype(bool)]
            if len(obs_alive) > 0:
                pstats.loc[a_id, 'avg_obs_dur'] = obs_alive.mean()[0]
            obs_loc = obs[obs['type'] == 'obs_log'].groupby(['key'])['key'].count()
            pstats.loc[a_id, 'repeated_obs'] = obs_loc.max()
        
        # items
        consumables = [
            'tango', 'enchanted_mango', 'faerie_fire', 'tango_single',
            'famango', 'great_famango', 'greater_famango',
            'flask', 'clarity'
            ]

        purchase_log = pd.DataFrame(player['purchase_log'])    
        def keycount(df, values):
            return df[df['key'].isin(values)].count()[0]
        pstats.loc[a_id, 'bought_rapier'] = keycount(purchase_log, ['rapier'])
        pstats.loc[a_id, 'bought_consumables'] = keycount(purchase_log, consumables)

        item_uses = pd.DataFrame([player['item_uses']]).T.reset_index()
        item_uses.rename({'index': 'key'}, axis = 1, inplace = True)
        def keysum(df, values):
            return df[df['key'].isin(values)].sum()[0]

        items = [
            'blood_grenade', 'enchanted_mango', 'smoke_of_deceit',
            'blink', 'armlet', 'revenants_brooch', 'pirate_hat'
            ]
        for item in items:
            pstats.loc[a_id, 'used_{}'.format(item)] = keysum(item_uses, [item])
        pstats.loc[a_id, 'trees_quelled'.format(item)] = keysum(item_uses, ['quelling_blade', 'bfury'])

        # buybacks
        #pstats.loc[a_id, 'buybacks'] = len(player['buyback_log'])

        # runes
        runes_log = pd.DataFrame(player['runes_log'])
        runes = ['bounty', 'wisdom']
        if len(runes_log) > 0:
            rune_dict = {i: 'power_rune' for i in range(10)}
            rune_dict.update({5: 'bounty', 8: 'wisdom', 7: 'water'})
            runes_log['key'] = runes_log['key'].apply(rune_dict.__getitem__)
            for rune in runes:
                pstats.loc[a_id, 'runes_{}'.format(rune)] = keycount(runes_log, [rune])
            pstats.loc[a_id, 'runes_6min'] = len(runes_log[(runes_log['key'] == 'power_rune') & (360 <= runes_log['time']) & (runes_log['time'] < 480)])
        else:
            for rune in runes:
                pstats.loc[a_id, 'runes_{}'.format(rune)] = 0
            pstats.loc[a_id, 'runes_6min'] = 0

        # kill streaks
        streaks = len(player['kill_streaks'])
        if streaks > 0:
            pstats.loc[a_id, 'kill_streak'] = streaks + 2
        else:
            pstats.loc[a_id, 'kill_streak'] = 0

        # damage source
        pstats.loc[a_id, 'blood_inflicted'] = player['damage_inflictor'].get('blood_grenade', 0)

        # map abilities
        pstats.loc[a_id, 'lotuses_stolen'] = player['ability_uses'].get('ability_pluck_famango', 0)
        pstats.loc[a_id, 'uses_high_five'] = player['ability_uses'].get('twin_gate_portal_warp', 0)
        pstats.loc[a_id, 'uses_portal'] = player['ability_uses'].get('plus_high_five', 0)

        # cosmetics
        cosmetics = pd.DataFrame(player['cosmetics'])
        if len(cosmetics) > 0:
            pstats.loc[a_id, 'cosmetics_count'] = len(cosmetics)
            pstats.loc[a_id, 'cosmetics_immortals'] = len(cosmetics[cosmetics['item_rarity'] == 'immortal'])
        else:
            pstats.loc[a_id, 'cosmetics_count'] = 0
            pstats.loc[a_id, 'cosmetics_immortals'] = 0
      
        # TODO:
        # units spawned or dominated    

    # other stats that aren't a single value
    #['max_hero_hit', 'times', 'gold_t', 'lh_t', 'dn_t', 'xp_t', 'obs_log',
    # 'sen_log', 'obs_left_log', 'sen_left_log', 'purchase_log', 'kills_log',
    # 'buyback_log', 'runes_log', 'connection_log', 'lane_pos', 'obs', 'sen',
    # 'actions', 'purchase', 'gold_reasons', 'xp_reasons', 'killed', 'item_uses',
    # 'ability_uses', 'ability_targets', 'damage_targets', 'hero_hits', 'damage',
    # 'damage_taken', 'damage_inflictor', 'runes', 'killed_by', 'kill_streaks',
    # 'multi_kills', 'life_state', 'healing', 'damage_inflictor_received',
    # 'permanent_buffs', 'ability_upgrades_arr', 'purchase_time',
    # 'first_purchase_time', 'item_win', 'item_usage', 'cosmetics', 'benchmarks']
    return pstats


## get all match player stats and merge
match_ids = data['match_id'].drop_duplicates()
pstats = pd.concat([get_match_player_stats(m) for m in match_ids])
pstats = pstats.reset_index().rename({'index': 'account_id'}, axis = 1)
div_stats = pd.merge(data, pstats, on = 'match_id', how = 'outer')

# save data
fname = 's{}_{}_div{}_{}.csv'.format(
    search['season'],
    search['league'][:3].lower(),
    search['division'],
    datestr(start_time, frmt = '%Y-%m-%d')
    )
div_stats.to_csv(os.path.join('stats', fname))

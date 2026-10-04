import requests, json, time, os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import rank2mmr
from utilities import datestr, read_google_sheet
from utilities2 import extract_account_id, extract_account_ids

## input

INPUT_PATH = 'input'
OUTPUT_PATH = 'sheets'
FNAME = 'rd2l_s34'

# match history search parameters
params = {'date': 180} # last 6 months
# TODO: put a date in the cache for opendota requests

update_mmrs = False
update_info = False
update_privacy = True
retry = False
save = True


## main
with open(os.path.join(INPUT_PATH, FNAME + '.json'), 'r') as f:
    rd2l = json.load(f)

# read player list
sheets = []
for season in rd2l['seasons']:
    for league in season['leagues'][:]:
        division = league['divisions'][0]
        sheets += [read_google_sheet(division['signups'], resolve_links = True)]

# Combine sheets
draft = pd.concat(sheets)

# Activity check
draft = draft[draft['Activity check'].isin(['Yes', 'yes'])].copy() # sometimes people edit this field by hand

# Owl and Moggoblin sheets ask for Dotabuff links for account ID
link_col_options = ['dotabuff link', 'stratz link', 'account link']
link_col = next(c for c in draft.columns if c.lower() in link_col_options) # get first match
draft['account_id'] = draft[link_col].apply(extract_account_id)

alts_col_options = ['second account', 'third account', 'please list your alternate accounts']
alts_cols = [c for c in draft.columns if c.lower() in alts_col_options]
alts = draft[alts_cols].fillna('').apply(' '.join, axis = 1)
draft['alt_ids'] = alts.apply(extract_account_ids)

# cleanup
draft = draft[[
    'Timestamp', 'Discord ID', 'Name', 'Have you played RD2L before?',
    'account_id', 'Alts', 'MMR', 'Screenshot', 'Activity check', 'alt_ids',
    ]].copy()
draft = draft.drop_duplicates([
    'Discord ID', 'Name', 'Have you played RD2L before?',
    'account_id', 'MMR', 'Screenshot',
    ])
draft = draft.reset_index(drop = True)

# extra columns
cols = [
    'games_total', 'patches_played', 'mmr_estimate', 'steam_name', 'privacy',
    ]
draft[cols] = None

# average rank of last 20 solo games
for i, player in list(draft.iterrows())[:]:

    accs = [player['account_id']]
    accs.extend(player['alt_ids'])
    print(i + 1, '/', len(draft), ':', accs)

    # mmr estimate
    mmr = player['MMR']
    if mmr < 5600:
        # find recent games of each account, get average rank
        # return highest mmr of all accounts
        # doesn't work on immortal+
        player_mmrs = {}
        for a in accs:
            matches = get_player_matches(a, **params, force = update_mmrs)
            if isinstance(matches, dict) and 'error' in matches:
                # try again
                # TODO: this should be in the opendota API code, not here
                matches = get_player_matches(a, **params, force = retry)
                if isinstance(matches, dict) and 'error' in matches:
                    # likely private profile
                    print('Error getting matches', a)
                    matches = []
            matches = sorted(matches, key = lambda x: x['start_time'], reverse = True)
            # solo normal or ranked games
            solo = [m for m in matches if m['party_size'] == 1 and m['lobby_type'] in [0, 7]]
            mmrs = [rank2mmr(m['average_rank'], -1) for m in solo]
            mmrs = [m for m in mmrs if m != 0][:20]
            if len(mmrs) >= 5 and all([m != 0 for m in mmrs]):
                # weighted average with 0.25 decay for bias towards recent games
                player_mmrs[a] = np.round(pd.Series(mmrs[::-1]).ewm(com = 2).mean().iloc[-1], -1)
        if len(player_mmrs) > 0:
            mmr2 = max(player_mmrs.values())
            if mmr2 - 100 >= mmr:
                # maybe error
                draft.loc[i, 'mmr_estimate'] = mmr2

    # experience
    history = []
    for a in accs:
        h = get_player_history(a, force = update_info)
        if isinstance(h, dict) and 'error' in h:
            # try again
            # TODO: this should be in the opendota API code, not here
            h = get_player_history(a, force = retry)
            if isinstance(h, dict) and 'error' in h:
                # likely private profile
                print('Error getting history', a)
                h = dict()
        history.append(h)

    if len(history) > 0 and any(h for h in history):
        history = [h for h in history if len(h) > 0]
        games_total = [h['leaver_status'] for h in history if h]
        games_total = [gt['0']['games'] for gt in games_total if gt]
        draft.loc[i, 'games_total'] = sum(games_total)
        patches = [p for h in history for p in list(h['patch'].keys())]
        draft.loc[i, 'patches_played'] = len(np.unique(patches))

    # info for liquipedia
    try:
        draft.loc[i, 'steam_name'] = get_player_data(accs[0], force = False)['name']
    except:
        pass

    # account privacy
    priv_st = [get_matches(account_id = a, force = update_privacy)['result']['status'] for a in accs]
    priv = [s == 15 for s in priv_st]
    if all(priv):
        draft.loc[i, 'privacy'] = 'private'
    elif any(priv):
        draft.loc[i, 'privacy'] = 'partial'
    else:
        draft.loc[i, 'privacy'] = 'public'

# cleanup
draft['account_id'] = draft['account_id'].apply(lambda x: f'https://dotabuff.com/players/{x}')
draft['alt_ids'] = draft['alt_ids'].apply(lambda acc: ', '.join([str(a) for a in acc]))
draft['Name'] = draft['Name'].astype(str)
draft = draft.sort_values('Name').reset_index(drop = True)

# save report
if save:
    fname = '{}_checksheet_{}.csv'.format(
        FNAME,
        datestr(time.time(), frmt = '%Y-%m-%d')
        )
    draft.to_csv(os.path.join(OUTPUT_PATH, fname), sep = ';')

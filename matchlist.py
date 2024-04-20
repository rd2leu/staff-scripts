import os, json
import pandas as pd
import numpy as np
from d2tools.api import *
from d2tools.utilities import *
from utilities import *

def gen_matchlist_roundrobin(teams, playdays = None):
    """
    Generates the group stage match list using the round-robin format

    playdays: use None for a full round robin (nb teams - 1)
    """
    return matchlist

def gen_matchlist_swiss(teams, **kwargs):
    """
    Generates the group stage match list using the swiss format
    """
    return matchlist

def gen_matchlist(teams, ml_format = 'roundrobin'):
    """
    Generates the group stage match list
    """
    return matchlist



## input
search = {
    'org': 'rd2l',
    'season': '28',
    'league': 'Sunday',
    'division': '2'
    }

timezone = 'CET'
start_time_str = 'December 24 2023 - 16:00'
start_time = datetoseconds(start_time_str, 'CET')
end_time = 2000000000

bestof = 3
force = False

encoding = 'utf-16'
encoding2 = 'utf16' # FIXME

## main

# read league info
team_info_str = search['org'], search['season'], encoding2
team_info_path = os.path.join('draft', '{}_s{}_{}.json'.format(*team_info_str))

with open(team_info_path, encoding = encoding) as f:
    season_info = json.load(f)

league_id = season_info_get(season_info, seasons = search['season'], leagues = search['league'])['id']
teams = season_info_get_teams(season_info, **search)
team_acc = {t['name']: [a for p in t['players'] for a in [p['account_id']] + p['alts']] for t in teams}

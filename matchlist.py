import os, json
import pandas as pd
import numpy as np
from d2tools.api import *
from d2tools.utilities import *
from utilities import *

INPUT_PATH = 'draft'
OUTPUT_PATH = 'groups'
FNAME = 'rd2l_s28'

with open(os.path.join(INPUT_PATH, FNAME + '_utf16.json'), 'r', encoding = 'utf-16') as f:
    rd2l = json.load(f)

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

def gen_matchlist(teams, ml_format = 'rr'):
    """
    Generates the group stage match list

    ml_format: {rr: round-robin, sw: swiss}
    """
    return matchlist

for season in rd2l['seasons']:
    for league in season['leagues']:
        for division in league['divisions']:
            print(season['name'], league['name'], division['name'])


teams = division['teams']

default_format = {
    'groupstage': 'round-robin',
    'playoffs': 'single elimination',
    }
format_ = division.get('format', default_format)

team_acc = {t['name']: [a for p in t['players'] for a in [p['account_id']] + p['alts']] for t in teams}

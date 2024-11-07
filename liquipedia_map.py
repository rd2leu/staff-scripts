import os
import pandas as pd
import numpy as np

from d2tools.api import *
from d2tools.utilities import *

hero_stats_path = os.path.join('input', 'hero_stats2.csv')

def gen_map_text(match_id, force = False, **team):
    """
    generate liquipedia match "Map" summary

    param match_id Match ID to lookup with opendota
    param **team Indicator to which side team1 is playing, default is radiant
    returns Map formatted string
    """

    template = """
|team1side={}
|t1h1={}|t1h2={}|t1h3={}|t1h4={}|t1h5={}
|t1b1={}|t1b2={}|t1b3={}|t1b4={}|t1b5={}|t1b6={}|t1b7={}
|team2side={}
|t2h1={}|t2h2={}|t2h3={}|t2h4={}|t2h5={}
|t2b1={}|t2b2={}|t2b3={}|t2b4={}|t2b5={}|t2b6={}|t2b7={}
|length={}|winner={}"""

    checks = {'team1': 'radiant',
              'team2': 'dire',
              'side1': 'radiant',
              'side2': 'dire',
              'team1side': 'radiant',
              'team2side': 'dire',
              'radiant': 1,
              'dire': 2}
    # all the different ways to check which side is team1
    check = (len(team) == 0) or any([(key in checks) and team[key] == checks[key] for key in team])
    check = int(check)

    data = get_match(match_id, force = force)
    draft = pd.DataFrame(data['picks_bans']).groupby(['team', 'is_pick']).agg(list)

    def pb_names(team = 0):
        """return list of names of heroes picked, banned"""
        hero_stats = pd.read_csv(hero_stats_path, sep = ';', index_col = 1)
        hero_stats['lname'] = hero_stats['localized_name'].apply(lambda x: x.lower())
        ids = []
        for f in [True, False]: # format is picks then bans (is_pick)
            picks, order = draft.loc[(team, f)]
            ids += np.array(picks)[np.argsort(order)].tolist()
            # TODO: insert gap when team doesn't ban a hero
        side = 'dire' if team else 'radiant' 
        return (side, *hero_stats['lname'][ids].values)

    """
    check	win	outcome
    1	1	1
    1	0	2
    0	1	2
    0	0	1
    """
    win = 1 + (data['radiant_win'] ^ check)
    # TODO: temporary fix people who forget to ban a hero
    names1 = list(pb_names(1 - check))
    names1 += [''] * (13 - len(names1))
    names2 = list(pb_names(check))
    names2 += [''] * (13 - len(names2))
    return template.format(*names1, *names2, shorttime(data['duration']), win)

if __name__ == '__main__':
    match_id = 7996993692
    print(gen_map_text(match_id, team1 = 'dire'))

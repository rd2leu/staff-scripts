import os
import pandas as pd
import numpy as np

from d2tools.api import get_match
from utilities import shorttime

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
              'team1_side': 'radiant',
              'team2_side': 'dire',
              'radiant': 1,
              'dire': 2}
    # all the different ways to check which side is team1
    check = (len(team) == 0) or any([(key in checks) and team[key] == checks[key] for key in team])
    check = int(check)

    data = get_match(match_id, force = force)
    draft = pd.DataFrame(data['picks_bans']).groupby(['team', 'is_pick']).agg(list)
    draft = draft[['hero_id', 'order']].copy()

    # convert hero ids to hero names
    hero_stats = pd.read_csv(hero_stats_path, sep = ';', index_col = 1)
    hero_stats['lname'] = hero_stats['localized_name'].apply(lambda x: x.lower())

    draft_names = []
    for (team, is_pick), (picks, order) in draft.iterrows():
        ids = np.array(picks)[np.argsort(order)].tolist()
        names = hero_stats['lname'][ids].to_list()
        draft_names += [names]
    draft['names'] = draft_names

    # prep data to fill in the template
    fill_in = {}
    team_indexes = draft.index.get_level_values('team').unique().to_list()
    team_indexes = sorted(team_indexes)
    pickban_counts = {True: 5, False: 7}
    # 5 picks 7 bans, each team 12
    # format is picks then bans
    for team in team_indexes:
        temp = []
        for is_pick, count in pickban_counts.items():
            names = []
            if (team, is_pick) in draft.index:
                names = draft.loc[(team, is_pick)]['names']
            # insert gap when team doesn't pick or ban a hero
            names.extend([''] * (count - len(names)))
            temp.extend(names)
        fill_in[team] = temp

    def pb_names(team = 0):
        side = 'dire' if team else 'radiant'
        return (side, *fill_in[team])

    """
    check	win	outcome
    1	1	1
    1	0	2
    0	1	2
    0	0	1
    """
    win = 1 + (data['radiant_win'] ^ check)
    names1 = list(pb_names(1 - check))
    names2 = list(pb_names(check))
    return template.format(*names1, *names2, shorttime(data['duration']), win)

if __name__ == '__main__':
    match_id = 8425751184
    print(gen_map_text(match_id, team1 = 'radiant'))
